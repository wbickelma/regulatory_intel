#!/usr/bin/env python3
"""
Test Workflow Script
====================

Demonstrates the full RSS feed ingestion workflow:
1. Generate RSS feed from a website URL via RSS.app
2. Subscribe to the feed in Inoreader and add to folder
3. Fetch recent articles from the folder

Usage:
    python scripts/test_workflow.py

Requirements:
    - .env file with API credentials and Inoreader tokens
"""

import os
import sys
import time
import requests

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from clients.rss_app import RssAppClient


# ============== CONFIGURATION ==============
# Loaded from .env file

INOREADER_APP_ID = os.getenv("CLIENT_ID_INOREADER")
INOREADER_APP_SECRET = os.getenv("CLIENT_SECRET_INOREADER")
INOREADER_ACCESS_TOKEN = os.getenv("INOREADER_ACCESS_TOKEN")
INOREADER_REFRESH_TOKEN = os.getenv("INOREADER_REFRESH_TOKEN")

RSSAPP_API_KEY = os.getenv("RSS_APP_KEY")
RSSAPP_API_SECRET = os.getenv("RSS_APP_SECRET")

# Test parameters
SOURCE_URL = "https://www.fedramp.gov/blog/1/"
TARGET_FOLDER = "test_folder2"
DAYS_BACK = 5


def refresh_access_token():
    """Refresh Inoreader access token if needed."""
    print("🔄 Refreshing access token...")
    response = requests.post(
        "https://www.inoreader.com/oauth2/token",
        data={
            "client_id": INOREADER_APP_ID,
            "client_secret": INOREADER_APP_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": INOREADER_REFRESH_TOKEN,
        }
    )
    if response.status_code == 200:
        tokens = response.json()
        print("✅ Token refreshed! Update INOREADER_ACCESS_TOKEN in .env with:")
        print(f"   {tokens['access_token']}")
        return tokens['access_token']
    else:
        print(f"❌ Failed to refresh token: {response.text}")
        return None


def add_feed_to_folder(feed_url: str, folder_name: str, access_token: str) -> bool:
    """Subscribe to feed and add to folder."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Step 1: Subscribe
    print(f"\n--- Subscribing to {feed_url} ---")
    add_res = requests.post(
        "https://www.inoreader.com/reader/api/0/subscription/quickadd",
        headers=headers,
        data={
            "quickadd": feed_url,
            "AppId": INOREADER_APP_ID,
            "AppKey": INOREADER_APP_SECRET
        }
    )
    
    if add_res.status_code == 401:
        new_token = refresh_access_token()
        if new_token:
            headers["Authorization"] = f"Bearer {new_token}"
            add_res = requests.post(
                "https://www.inoreader.com/reader/api/0/subscription/quickadd",
                headers=headers,
                data={"quickadd": feed_url, "AppId": INOREADER_APP_ID, "AppKey": INOREADER_APP_SECRET}
            )
    
    if add_res.status_code != 200:
        print(f"❌ Failed to subscribe: {add_res.text}")
        return False
    
    feed_id = add_res.json().get('streamId')
    print(f"✅ Subscribed! Feed ID: {feed_id}")
    
    # Step 2: Add to folder
    print(f"\n--- Moving feed to folder: '{folder_name}' ---")
    tag_res = requests.post(
        "https://www.inoreader.com/reader/api/0/subscription/edit",
        headers=headers,
        data={
            "ac": "edit",
            "s": feed_id,
            "a": f"user/-/label/{folder_name}",
            "AppId": INOREADER_APP_ID,
            "AppKey": INOREADER_APP_SECRET
        }
    )
    
    if tag_res.status_code == 200:
        print(f"🚀 Successfully added feed to '{folder_name}'!")
        return True
    else:
        print(f"❌ Failed to move to folder: {tag_res.text}")
        return False


def get_folder_articles(folder_name: str, access_token: str, days_back: int = 7) -> list:
    """Fetch articles from folder."""
    print(f"\n--- Fetching articles from '{folder_name}' (Last {days_back} days) ---")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    cutoff_time = int(time.time()) - (days_back * 24 * 60 * 60)
    
    response = requests.get(
        f"https://www.inoreader.com/reader/api/0/stream/contents/user/-/label/{folder_name}",
        headers=headers,
        params={
            "AppId": INOREADER_APP_ID,
            "AppKey": INOREADER_APP_SECRET,
            "n": 50,
            "ot": cutoff_time
        }
    )
    
    if response.status_code == 401:
        new_token = refresh_access_token()
        if new_token:
            headers["Authorization"] = f"Bearer {new_token}"
            response = requests.get(
                f"https://www.inoreader.com/reader/api/0/stream/contents/user/-/label/{folder_name}",
                headers=headers,
                params={"AppId": INOREADER_APP_ID, "AppKey": INOREADER_APP_SECRET, "n": 50, "ot": cutoff_time}
            )
    
    if response.status_code != 200:
        print(f"❌ Error fetching articles: {response.text}")
        return []
    
    items = response.json().get('items', [])
    print(f"✅ Found {len(items)} articles.\n")
    
    for item in items:
        title = item.get('title', 'No Title')
        pub_ts = item.get('published', 0)
        pub_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(pub_ts))
        link = item.get('canonical', [{}])[0].get('href', 'No Link')
        print(f"📰 {title}\n🕒 {pub_date}\n🔗 {link}\n")
    
    return items


def main():
    """Run the full test workflow."""
    print("=" * 60)
    print("📡 REGULATORY INTELLIGENCE - TEST WORKFLOW")
    print("=" * 60)
    
    # Verify credentials are loaded
    required = [INOREADER_APP_ID, INOREADER_APP_SECRET, INOREADER_ACCESS_TOKEN, RSSAPP_API_KEY, RSSAPP_API_SECRET]
    if not all(required):
        print("\n❌ Missing credentials in .env file!")
        print("Required variables:")
        print(f"  CLIENT_ID_INOREADER:      {'✅' if INOREADER_APP_ID else '❌ MISSING'}")
        print(f"  CLIENT_SECRET_INOREADER:  {'✅' if INOREADER_APP_SECRET else '❌ MISSING'}")
        print(f"  INOREADER_ACCESS_TOKEN:   {'✅' if INOREADER_ACCESS_TOKEN else '❌ MISSING'}")
        print(f"  RSS_APP_KEY:              {'✅' if RSSAPP_API_KEY else '❌ MISSING'}")
        print(f"  RSS_APP_SECRET:           {'✅' if RSSAPP_API_SECRET else '❌ MISSING'}")
        return
    
    print("\n✅ All credentials loaded from .env")
    
    # --- Step 1: Generate RSS Feed ---
    print("\n[STEP 1] Generating RSS feed via RSS.app...")
    
    rss_client = RssAppClient(
        api_key=RSSAPP_API_KEY,
        api_secret=RSSAPP_API_SECRET
    )
    
    feed_response = rss_client.create_feed_sync(SOURCE_URL)
    
    if not feed_response:
        print("❌ Failed to generate RSS feed. Exiting.")
        return
    
    feed_url = feed_response.feed_url
    
    # --- Step 2: Subscribe in Inoreader ---
    print("\n[STEP 2] Subscribing feed to Inoreader folder...")
    
    add_feed_to_folder(feed_url, TARGET_FOLDER, INOREADER_ACCESS_TOKEN)
    
    # --- Step 3: Fetch Articles ---
    print(f"\n[STEP 3] Fetching articles from '{TARGET_FOLDER}' (last {DAYS_BACK} days)...")
    
    articles = get_folder_articles(TARGET_FOLDER, INOREADER_ACCESS_TOKEN, DAYS_BACK)
    
    # --- Summary ---
    print("\n" + "=" * 60)
    print("📊 WORKFLOW SUMMARY")
    print("=" * 60)
    print(f"Source URL:     {SOURCE_URL}")
    print(f"RSS Feed URL:   {feed_url}")
    print(f"Target Folder:  {TARGET_FOLDER}")
    print(f"Articles Found: {len(articles)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
