#!/usr/bin/env python3
"""Test RSS.app feed creation for a source URL."""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from clients.rss_app import RssAppClient

SOURCE_URL = (
    "https://www.skadden.com/insights"
    "?skip=0&panelid=tab-find-mode&paneltogglestate=2"
    "&type=9cbfe518-3bc0-4632-ae13-6ac9cee8eb31&hassearched=true"
)

def main():
    api_key = os.getenv("RSS_APP_KEY")
    api_secret = os.getenv("RSS_APP_SECRET")

    if not api_key:
        print("❌ RSS_APP_KEY environment variable not set")
        return
    
    print(f"Using API key: {api_key[:8]}...{api_key[-4:]}")
    print(f"Key length: {len(api_key)}")
    
    client = RssAppClient(api_key, api_secret)
    result = client.create_feed_sync(SOURCE_URL)
    
    if result:
        print(f"\n✅ Success!")
        print(f"   Feed ID: {result.feed_id}")
        print(f"   Feed URL: {result.feed_url}")
        print(f"   Title: {result.title}")
    else:
        print("\n❌ Failed to create feed")

if __name__ == "__main__":
    main()
