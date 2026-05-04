#!/usr/bin/env python3
"""
Fetch Feed Script
=================

Downloads article metadata from an Inoreader folder and saves to data/test_feed.json.

Usage:
    python scripts/fetch_feed.py
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

FEED_FILE = os.path.join(DATA_DIR, "test_feed.json")


def main():
    print("=" * 60)
    print("📥 FETCH FEED")
    print("=" * 60)

    creds = load_credentials()
    inoreader = get_inoreader_client(creds)

    print(f"\nFetching articles from '{TARGET_FOLDER}' (last {DAYS_BACK} day(s))...")
    articles = inoreader.get_folder_articles_sync(
        TARGET_FOLDER, days_back=DAYS_BACK
    )

    if not articles:
        print("⚠️  No articles found in timeframe.")
        return

    records = [
        {
            "item_id": a.item_id,
            "title": a.title,
            "url": a.url,
            "published_at": a.published_at.isoformat(),
            "summary": a.summary or "",
            "full_content": a.full_content or "",
            "relevance_score": a.relevance_score,
        }
        for a in articles
    ]

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(FEED_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved {len(records)} articles → {FEED_FILE}")


if __name__ == "__main__":
    main()
