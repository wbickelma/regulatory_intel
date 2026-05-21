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

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from clients.rss_app import RssAppClient
from clients.inoreader import InoreaderClient, InoreaderAuthManager


# ============== CONFIGURATION ==============

# Test parameters
SOURCE_URL = "https://www.fedramp.gov/blog/1/"
TARGET_FOLDER = "Cybersecurity"
DAYS_BACK = 5


def main():
    """Run the full test workflow."""
    print("=" * 60)
    print("📡 REGULATORY INTELLIGENCE - TEST WORKFLOW")
    print("=" * 60)

    # Load credentials from .env
    app_id = os.getenv("CLIENT_ID_INOREADER")
    app_key = os.getenv("CLIENT_SECRET_INOREADER")
    access_token = os.getenv("INOREADER_ACCESS_TOKEN")
    refresh_token = os.getenv("INOREADER_REFRESH_TOKEN")
    rss_key = os.getenv("RSS_APP_KEY")
    rss_secret = os.getenv("RSS_APP_SECRET")

    # Verify credentials are loaded
    creds = {
        "CLIENT_ID_INOREADER": app_id,
        "CLIENT_SECRET_INOREADER": app_key,
        "INOREADER_ACCESS_TOKEN": access_token,
        "RSS_APP_KEY": rss_key,
        "RSS_APP_SECRET": rss_secret,
    }
    if not all(creds.values()):
        print("\n❌ Missing credentials in .env file!")
        print("Required variables:")
        for name, val in creds.items():
            print(f"  {name:30s} {'✅' if val else '❌ MISSING'}")
        return

    print("\n✅ All credentials loaded from .env")

    # Initialize clients
    auth_manager = InoreaderAuthManager(
        app_id=app_id,
        app_key=app_key,
        access_token=access_token,
        refresh_token=refresh_token,
    )
    inoreader = InoreaderClient(
        app_id=app_id,
        app_key=app_key,
        auth_manager=auth_manager,
    )
    rss_client = RssAppClient(api_key=rss_key, api_secret=rss_secret)

    # --- Step 1: Generate RSS Feed ---
    print("\n[STEP 1] Generating RSS feed via RSS.app...")

    feed_response = rss_client.create_feed_sync(SOURCE_URL)

    if not feed_response:
        print("❌ Failed to generate RSS feed. Exiting.")
        return

    feed_url = feed_response.feed_url

    # --- Step 2: Subscribe in Inoreader ---
    print("\n[STEP 2] Subscribing feed to Inoreader folder...")

    inoreader.add_feed_to_folder_sync(feed_url, TARGET_FOLDER)

    # --- Step 3: Fetch Articles ---
    print(f"\n[STEP 3] Fetching articles from '{TARGET_FOLDER}' (last {DAYS_BACK} days)...")

    articles = inoreader.get_folder_articles_sync(TARGET_FOLDER, days_back=DAYS_BACK)

    # --- Step 4: Fetch Full Content ---
    CONTENT_PREVIEW_LIMIT = 3
    print(f"\n[STEP 4] Fetching full content for first {CONTENT_PREVIEW_LIMIT} articles via Mobilizer...")

    for article in articles[:CONTENT_PREVIEW_LIMIT]:
        print(f"\n{'─' * 60}")
        print(f"📰 {article.title}")
        print(f"🔗 {article.url}")
        content = inoreader.get_article_content_sync(article.item_id)
        if content:
            # Strip HTML for readable preview
            plain = InoreaderClient._strip_html(content)
            preview = plain[:500] + ("..." if len(plain) > 500 else "")
            print(f"📄 Content preview:\n{preview}")
        else:
            print("⚠️  No full content available (Mobilizer returned empty/error)")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("📊 WORKFLOW SUMMARY")
    print("=" * 60)
    print(f"Source URL:     {SOURCE_URL}")
    print(f"RSS Feed URL:   {feed_url}")
    print(f"Target Folder:  {TARGET_FOLDER}")
    print(f"Articles Found: {len(articles)}")
    print(f"Full Content:   Fetched for {min(CONTENT_PREVIEW_LIMIT, len(articles))} articles")
    print("=" * 60)


if __name__ == "__main__":
    main()
