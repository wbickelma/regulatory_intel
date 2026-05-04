#!/usr/bin/env python3
"""
Fetch Full Content Script
=========================

Reads article metadata from data/test_feed.json and enriches each article
with full content via the Inoreader Mobilizer API.

Usage:
    python scripts/fetch_full_content.py
"""
from __future__ import annotations

import json
import os

from common import (
    DATA_DIR,
    TARGET_FOLDER,
    DAYS_BACK,
    load_credentials,
    get_inoreader_client,
)
from clients.inoreader import InoreaderClient

FEED_FILE = os.path.join(DATA_DIR, "test_feed.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "test_full_content.json")
MAX_ARTICLES = 10


def main():
    print("=" * 60)
    print("📄 FETCH FULL CONTENT")
    print("=" * 60)

    if not os.path.exists(FEED_FILE):
        print(f"❌ {FEED_FILE} not found. Run fetch_feed.py first.")
        return

    with open(FEED_FILE, "r", encoding="utf-8") as f:
        articles = json.load(f)

    articles = articles[:MAX_ARTICLES]
    print(f"\nProcessing first {len(articles)} articles from {FEED_FILE}")

    creds = load_credentials()
    inoreader = get_inoreader_client(creds)

    for article in articles:
        print(f"\n{'─' * 60}")
        print(f"📰 {article['title']}")
        print(f"🔗 {article['url']}")

        content = inoreader.get_article_content_sync(article["item_id"])
        if content:
            plain = InoreaderClient._strip_html(content)
            preview = plain[:500] + ("..." if len(plain) > 500 else "")
            print(f"📄 Content preview:\n{preview}")
            article["full_content"] = plain
        else:
            print("⚠️  No full content available (Mobilizer returned empty/error)")
            article["full_content"] = ""

        # Preserve relevance_score (default to null if not present)
        article.setdefault("relevance_score", None)

    # Save enriched data
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

    # --- Summary ---
    with_content = sum(1 for a in articles if a["full_content"])
    print("\n" + "=" * 60)
    print("📊 FETCH SUMMARY")
    print("=" * 60)
    print(f"Folder:         {TARGET_FOLDER}")
    print(f"Timeframe:      Last {DAYS_BACK} day(s)")
    print(f"Articles:       {len(articles)}")
    print(f"Full Content:   {with_content}/{len(articles)}")
    print(f"Saved to:       {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
