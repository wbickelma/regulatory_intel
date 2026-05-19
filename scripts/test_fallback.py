#!/usr/bin/env python3
"""
Test Fallback Content Fetching
==============================

1. Download articles from the last 2 days (or load from cache)
2. Try Inoreader Mobilizer for full content
3. Save failed articles to cache file
4. Test fallback methods (Playwright, ScrapegraphAI, Gemini)

Usage:
    python scripts/test_fallback.py           # Use cached failures if available
    python scripts/test_fallback.py --refresh # Force re-fetch from API
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.common import DATA_DIR, load_credentials, get_inoreader_client
from clients.content_fetcher import fetch_content_with_fallback
from clients.inoreader import ArticleItem

TARGET_FOLDER = "test_folder1"
DAYS_BACK = 2
OUTPUT_FILE = os.path.join(DATA_DIR, "fallback_test_results.json")
FAILED_CACHE_FILE = os.path.join(DATA_DIR, "failed_articles_cache.json")
FALLBACK_SUCCESS_FILE = os.path.join(DATA_DIR, "fallback_success_cache.json")


def load_failed_from_cache() -> list:
    """Load previously failed articles from cache."""
    print(f"   Looking for cache at: {FAILED_CACHE_FILE}")
    if not os.path.exists(FAILED_CACHE_FILE):
        print("   ❌ Cache file not found")
        return []
    try:
        print("   ✅ Cache file found, loading...")
        with open(FAILED_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        articles = [ArticleItem.from_dict(d) for d in data]
        print(f"   ✅ Loaded {len(articles)} articles from cache")
        return articles
    except Exception as e:
        print(f"⚠️ Could not load cache: {e}")
        return []


def save_failed_to_cache(articles: list):
    """Save failed articles to cache for future runs."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(FAILED_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump([a.to_dict() for a in articles], f, indent=2, ensure_ascii=False)
    print(f"💾 Saved {len(articles)} failed articles to: {FAILED_CACHE_FILE}")


def save_fallback_successes(articles: list):
    """Save articles where fallback methods succeeded."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(FALLBACK_SUCCESS_FILE, "w", encoding="utf-8") as f:
        json.dump([a.to_dict() for a in articles], f, indent=2, ensure_ascii=False)
    print(f"💾 Saved {len(articles)} fallback successes to: {FALLBACK_SUCCESS_FILE}")


def fetch_and_test_inoreader() -> tuple[list, list]:
    """Fetch articles from API and test Inoreader Mobilizer."""
    print(f"\n[STEP 1] Fetching articles from '{TARGET_FOLDER}' (last {DAYS_BACK} days)...")
    creds = load_credentials()
    inoreader = get_inoreader_client(creds)
    
    articles = inoreader.get_folder_articles_sync(TARGET_FOLDER, days_back=DAYS_BACK)
    print(f"✅ Found {len(articles)} articles")

    if not articles:
        return [], []

    print(f"\n[STEP 2] Testing Inoreader Mobilizer on {len(articles)} articles...")
    
    success_inoreader = []
    failed_inoreader = []
    
    for i, article in enumerate(articles, 1):
        print(f"  [{i}/{len(articles)}] {article.title[:50]}...", end=" ")
        
        content = inoreader.get_article_content_sync(article.item_id)
        if content:
            plain = inoreader._strip_html(content)
            if plain and len(plain.strip()) >= 100:
                article.full_content = plain
                success_inoreader.append(article)
                print("✅ Inoreader OK")
            else:
                failed_inoreader.append(article)
                print("❌ Too short")
        else:
            failed_inoreader.append(article)
            print("❌ Empty")

    print(f"\n📊 Inoreader Results:")
    print(f"  ✅ Success: {len(success_inoreader)}")
    print(f"  ❌ Failed:  {len(failed_inoreader)}")
    
    # Save failures to cache
    if failed_inoreader:
        save_failed_to_cache(failed_inoreader)
    
    return success_inoreader, failed_inoreader


def main():
    print("=" * 70)
    print("🧪 FALLBACK CONTENT FETCHER TEST")
    print("=" * 70)

    # Check for --refresh flag
    force_refresh = "--refresh" in sys.argv
    
    # Try loading from cache first (unless --refresh)
    if not force_refresh:
        print("\n[CACHE] Checking for cached failed articles...")
        cached_failures = load_failed_from_cache()
        if cached_failures:
            print(f"\n📂 Using {len(cached_failures)} failed articles from cache")
            print(f"   (Use --refresh to re-fetch from API)")
            failed_inoreader = cached_failures
            success_inoreader = []  # Unknown from cache
        else:
            print("\n[CACHE] No cache found, fetching from API...")
            success_inoreader, failed_inoreader = fetch_and_test_inoreader()
    else:
        print("\n🔄 Force refresh requested, ignoring cache...")
        success_inoreader, failed_inoreader = fetch_and_test_inoreader()

    if not failed_inoreader:
        print("\n✨ No failed articles to test. Exiting.")
        return

    # Test on up to 5 failed articles
    test_batch = failed_inoreader[:5]
    print(f"\n[STEP 3] Testing fallback methods on {len(test_batch)} articles...")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_failed": len(failed_inoreader),
        "tested_count": len(test_batch),
        "fallback_tests": []
    }
    
    fallback_successes = []  # Track articles where fallback worked

    for i, article in enumerate(test_batch, 1):
        print(f"\n{'─' * 70}")
        print(f"[{i}/{len(test_batch)}] Testing: {article.title}")
        print(f"    Source: {article.source}")
        print(f"    URL: {article.url}")
        print("─" * 70)
        
        # Run fallback chain
        success = fetch_content_with_fallback(article)
        
        test_result = {
            "title": article.title,
            "url": article.url,
            "source": article.source,
            "success": success,
            "full_content_length": len(article.full_content) if article.full_content else 0,
            "ai_summary_length": len(article.ai_summary) if article.ai_summary else 0,
            "method_used": None
        }
        
        if article.full_content:
            test_result["method_used"] = "playwright"
            preview = article.full_content[:300]
            print(f"\n✅ PLAYWRIGHT SUCCESS ({len(article.full_content)} chars)")
            print(f"   Preview: {preview}...")
            fallback_successes.append(article)
        elif article.ai_summary:
            test_result["method_used"] = "scrapegraph_or_gemini"
            preview = article.ai_summary[:300]
            print(f"\n✅ AI SUMMARY SUCCESS ({len(article.ai_summary)} chars)")
            print(f"   Preview: {preview}...")
            fallback_successes.append(article)
        else:
            print("\n❌ ALL METHODS FAILED")
        
        results["fallback_tests"].append(test_result)

    # --- Step 4: Save results ---
    print(f"\n[STEP 4] Saving results...")
    os.makedirs(DATA_DIR, exist_ok=True)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"   Saved test results to: {OUTPUT_FILE}")
    
    # Save successful fallback articles
    if fallback_successes:
        save_fallback_successes(fallback_successes)

    # --- Summary ---
    print("\n" + "=" * 70)
    print("📊 FINAL SUMMARY")
    print("=" * 70)
    
    fallback_success = sum(1 for t in results["fallback_tests"] if t["success"])
    playwright_count = sum(1 for t in results["fallback_tests"] if t["method_used"] == "playwright")
    ai_count = sum(1 for t in results["fallback_tests"] if t["method_used"] == "scrapegraph_or_gemini")
    
    print(f"  Failed articles (cached): {len(failed_inoreader)}")
    print(f"  Fallback tested:          {len(test_batch)}")
    print(f"  Fallback success:         {fallback_success}")
    print(f"    - via Playwright:       {playwright_count}")
    print(f"    - via AI Summary:       {ai_count}")
    print(f"\n  Results saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
