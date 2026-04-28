#!/usr/bin/env python3
"""
Onboard Feed Script
===================

Generates an RSS feed from a website URL and subscribes it in Inoreader.

Steps:
  1. Generate RSS feed via RSS.app
  2. Subscribe the feed in Inoreader and tag to folder

Usage:
    python scripts/onboard_feed.py
"""
from __future__ import annotations

from common import (
    SOURCE_URL,
    TARGET_FOLDER,
    load_credentials,
    get_inoreader_client,
    get_rss_client,
)


def main():
    print("=" * 60)
    print("📡 ONBOARD FEED")
    print("=" * 60)

    creds = load_credentials()
    rss_client = get_rss_client(creds)
    inoreader = get_inoreader_client(creds)

    # --- Step 1: Generate RSS Feed ---
    print(f"\n[STEP 1] Generating RSS feed for: {SOURCE_URL}")
    feed_response = rss_client.create_feed_sync(SOURCE_URL)

    if not feed_response:
        print("❌ Failed to generate RSS feed. Exiting.")
        return

    feed_url = feed_response.feed_url

    # --- Step 2: Subscribe in Inoreader ---
    print(f"\n[STEP 2] Subscribing feed to Inoreader folder '{TARGET_FOLDER}'...")
    inoreader.add_feed_to_folder_sync(feed_url, TARGET_FOLDER)

    # --- Summary ---
    print("\n" + "=" * 60)
    print("📊 ONBOARD SUMMARY")
    print("=" * 60)
    print(f"Source URL:    {SOURCE_URL}")
    print(f"RSS Feed URL:  {feed_url}")
    print(f"Target Folder: {TARGET_FOLDER}")
    print("=" * 60)


if __name__ == "__main__":
    main()
