import csv
import json
import requests
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from clients.inoreader import InoreaderAuthManager

# --- CONFIGURATION ---
APP_ID = os.getenv("CLIENT_ID_INOREADER")
APP_KEY = os.getenv("CLIENT_SECRET_INOREADER")

# Mapping the agencies to their respective countries based on your specifications
AGENCY_COUNTRY_MAP = {
    "CFR": ("US", "United States"), "Congress": ("US", "United States"),
    "FCC": ("US", "United States"), "FDA": ("US", "United States"),
    "Fed Register": ("US", "United States"), "FTC": ("US", "United States"),
    "NIST": ("US", "United States"),
    "EC Have Your Say": ("EU", "European Union"), "EDPB": ("EU", "European Union"),
    "ENISA": ("EU", "European Union"), "EUR-Lex": ("EU", "European Union"),
    "FCA": ("GB", "United Kingdom"), "ICO": ("GB", "United Kingdom"),
    "legislation.gov": ("GB", "United Kingdom"), "Ofcom": ("GB", "United Kingdom"),
    "Canada Gazette": ("CA", "Canada"), "ISED": ("CA", "Canada"), "OPC": ("CA", "Canada"),
    "IMDA": ("SG", "Singapore"), "PDPC": ("SG", "Singapore"),
    "MIC": ("JP", "Japan"), "PPC": ("JP", "Japan"),
    "ACMA": ("AU", "Australia"), "OAIC": ("AU", "Australia")
}

def determine_country(feed_title: str) -> tuple[str, str]:
    """Helper to guess the country based on the feed title."""
    for agency, (code, name) in AGENCY_COUNTRY_MAP.items():
        if agency.lower() in feed_title.lower():
            return code, name
    return "US", "United States" # Default fallback

def fetch_and_export():
    auth_manager = InoreaderAuthManager(app_id=APP_ID, app_key=APP_KEY)
    access_token = auth_manager.get_access_token_sync()
    
    print("Fetching subscriptions from Inoreader...")
    response = requests.get(
        "https://www.inoreader.com/reader/api/0/subscription/list",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"AppId": APP_ID, "AppKey": APP_KEY}
    )
    response.raise_for_status()
    subscriptions = response.json().get("subscriptions", [])
    
    # Data structures for CSVs
    countries_dict = {} # {code: name}
    topics_dict = {}    # {name: id}
    sources_list = []   # [{source_id, name, country_code, stream_id, url}]
    source_topics = []  # [(source_id, topic_id)]
    
    topic_counter = 1
    source_counter = 1
    
    print(f"Processing {len(subscriptions)} subscriptions...")
    for sub in subscriptions:
        stream_id = sub.get("id")
        title = sub.get("title", "Unknown Source")
        url = sub.get("url", "")
        
        # Determine Country
        country_code, country_name = determine_country(title)
        countries_dict[country_code] = country_name
        
        # Add Source
        sources_list.append({
            "source_id": source_counter,
            "source_name": title,
            "country_code": country_code,
            "inoreader_stream_id": stream_id,
            "feed_url": url,
            "last_fetched_at": None,
            "is_active": True
        })
        
        # Process Topics (Inoreader categories)
        categories = sub.get("categories", [])
        for cat in categories:
            # Extract clean folder name from "user/-/label/FolderName"
            topic_name = cat.get("label", "").split("/")[-1]
            
            if not topic_name:
                continue
                
            if topic_name not in topics_dict:
                topics_dict[topic_name] = topic_counter
                topic_counter += 1
                
            # Map Source to Topic
            source_topics.append({
                "source_id": source_counter,
                "topic_id": topics_dict[topic_name]
            })
            
        source_counter += 1

    # --- WRITE CSVS ---
    output_dir = os.path.join(PROJECT_ROOT, "data")
    os.makedirs(output_dir, exist_ok=True)
    print(f"Writing CSV files to {output_dir}...")
    
    with open(os.path.join(output_dir, 'countries.csv'), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['country_code', 'country_name'])
        for code, name in countries_dict.items():
            writer.writerow([code, name])
            
    with open(os.path.join(output_dir, 'topics.csv'), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['topic_id', 'topic_name'])
        for name, t_id in topics_dict.items():
            writer.writerow([t_id, name])
            
    with open(os.path.join(output_dir, 'sources.csv'), 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=sources_list[0].keys())
        writer.writeheader()
        writer.writerows(sources_list)
            
    with open(os.path.join(output_dir, 'source_topics.csv'), 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['source_id', 'topic_id'])
        writer.writeheader()
        writer.writerows(source_topics)
        
    print("✅ Export complete! Generated: countries.csv, topics.csv, sources.csv, source_topics.csv")

if __name__ == "__main__":
    fetch_and_export()