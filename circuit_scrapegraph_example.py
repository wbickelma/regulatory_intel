import os
import json
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Import your firm's authentication requirements
import time
import requests
import base64

# Import LangChain's Azure integration and ScrapeGraphAI
from langchain_openai import AzureChatOpenAI
from scrapegraphai.graphs import SmartScraperGraph

# Load .env
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

model_name = "gpt-5-nano"
# --- 1. YOUR FIRM's AUTHENTICATION CLASS ---
class CircuitApi:
    def __init__(self, appkey=None):
        self.appkey = appkey or os.getenv("CIRCUIT_APPKEY")
        self.api_version = "2025-04-01-preview"
        self.base_url = 'https://chat-ai.cisco.com/'
        self.token = self._fetch_token()

    def _fetch_token(self):
        url = "https://id.cisco.com/oauth2/default/v1/token"
        payload = "grant_type=client_credentials"
        client_id = os.getenv("CIRCUIT_CLIENT_ID")
        client_secret = os.getenv("CIRCUIT_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError("Missing CIRCUIT_CLIENT_ID or CIRCUIT_CLIENT_SECRET")

        value = base64.b64encode(f'{client_id}:{client_secret}'.encode('utf-8')).decode('utf-8')
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {value}"
        }
        token_response = requests.post(url, headers=headers, data=payload)
        token_response.raise_for_status()
        
        return token_response.json().get("access_token")


# --- 2. PIPELINE INITIALIZATION ---
print("Authenticating with Circuit API...")
circuit = CircuitApi()

# Create a LangChain LLM instance utilizing your firm's token and parameters
llm_instance = AzureChatOpenAI(
    azure_endpoint=circuit.base_url,
    openai_api_version=circuit.api_version,
    api_key=circuit.token,
    model_name=model_name, 
    temperature=0.0,
    model_kwargs={"user": f'{{"appkey": "{circuit.appkey}"}}'} 
)

# Configure ScrapeGraphAI with Playwright stealth browser.
# ScrapegraphAI's ChromiumLoader already uses undetected_playwright with
# Malenia.apply_stealth() by default — no explicit "stealth" flag needed.
# Key tuning knobs are timeout, load_state, and headless.
graph_config = {
    "llm": {
        "model_instance": llm_instance,
        "model_tokens": 128000
    },
    "loader_kwargs": {
        "timeout": 60,                         # Give the page more time to load
        "load_state": "networkidle",            # Wait until network is idle (all resources loaded)
    },
    "verbose": True,
    "headless": True  # Set to False to visually debug CAPTCHA issues
}

# --- 3. DEFINE OUTPUT SCHEMA ---
# Using a Pydantic schema forces the LLM to return structured, multi-document output
# instead of freeform text or a single result.
class RegulatoryDocument(BaseModel):
    title: str = Field(description="The full title of the regulatory document")
    publication_date: str = Field(description="Publication date in YYYY-MM-DD format")
    agency: str = Field(description="The issuing agency name")
    document_type: Optional[str] = Field(default=None, description="Type of document (Rule, Proposed Rule, Notice, etc.)")

class ExtractionResult(BaseModel):
    documents: List[RegulatoryDocument] = Field(description="List of all regulatory documents found on the page")

# --- 4. EXECUTE THE SCRAPE ---
target_url = "https://www.federalregister.gov/documents/current"
extraction_prompt = (
    "Extract ALL regulatory documents listed on this page. "
    "For each document, extract the title, publication date, agency, and document type. "
    "Return every document you can find, not just the first one."
)

print(f"\nStarting Playwright stealth extraction on: {target_url}...")

smart_scraper = SmartScraperGraph(
    prompt=extraction_prompt,
    source=target_url,
    schema=ExtractionResult,
    config=graph_config
)

try:
    result = smart_scraper.run()
    print("\n--- Extraction Complete ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"\nAn error occurred during the scrape: {e}")