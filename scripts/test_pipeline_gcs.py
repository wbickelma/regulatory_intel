#!/usr/bin/env python3
"""
Test script: Full pipeline - fetch, evaluate, get content, save to GCS.
"""
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from config.settings import TOPIC_FOLDERS, settings
from scripts.common import get_inoreader_client, load_credentials
from clients.gcs_client import GCSClient
from clients.content_fetcher import fetch_content_with_fallback
from evaluation.scorer import evaluate_articles

RELEVANCE_THRESHOLD = 6
DAYS_BACK = 1


def main():
    print("=" * 60)
    print("🧪 FULL PIPELINE → GCS TEST")
    print("=" * 60)
    print(f"Topics: {TOPIC_FOLDERS}")
    print(f"Days back: {DAYS_BACK}")
    print(f"Relevance threshold: {RELEVANCE_THRESHOLD}")
    print()

    # Initialize clients
    creds = load_credentials()
    inoreader = get_inoreader_client(creds)
    gcs = GCSClient()

    results_summary = []

    for topic in TOPIC_FOLDERS:
        print(f"\n{'='*60}")
        print(f"📁 {topic}")
        print("=" * 60)

        # Step 1: Fetch articles
        print(f"\n[1/4] Fetching articles...")
        try:
            articles = inoreader.get_folder_articles_sync(topic, days_back=DAYS_BACK)
            print(f"      Found: {len(articles)} articles")
        except Exception as e:
            print(f"      ❌ Fetch failed: {e}")
            results_summary.append({"topic": topic, "status": "fetch_failed", "fetched": 0, "passed": 0, "saved": 0})
            continue

        if not articles:
            print(f"      No articles found")
            results_summary.append({"topic": topic, "status": "no_articles", "fetched": 0, "passed": 0, "saved": 0})
            continue

        # Step 2: Evaluate articles
        print(f"\n[2/4] Evaluating {len(articles)} articles...")
        evaluated = evaluate_articles(articles)
        
        high_scorers = [
            a for a in evaluated
            if a.relevance_score is not None and a.relevance_score >= RELEVANCE_THRESHOLD
        ]
        print(f"      Passed threshold: {len(high_scorers)}/{len(articles)}")

        if not high_scorers:
            print(f"      No articles passed evaluation")
            results_summary.append({"topic": topic, "status": "none_passed", "fetched": len(articles), "passed": 0, "saved": 0})
            continue

        # Step 3: Fetch full content with fallback
        print(f"\n[3/4] Fetching full content for {len(high_scorers)} articles...")
        enriched = []
        for i, article in enumerate(high_scorers):
            print(f"      [{i+1}/{len(high_scorers)}] {article.title[:50]}...")
            
            # Try Inoreader mobilizer first
            if not article.full_content or len(article.full_content) < 500:
                try:
                    mobilized = inoreader.get_article_content_sync(article.item_id)
                    if mobilized and len(mobilized) > len(article.full_content or ""):
                        article.full_content = mobilized
                        print(f"            ✓ Mobilizer: {len(mobilized)} chars")
                except:
                    pass
            
            # Fallback if still no good content
            if not article.full_content or len(article.full_content) < 500:
                success = fetch_content_with_fallback(article)
                if success and article.full_content:
                    print(f"            ✓ Fallback: {len(article.full_content)} chars")
                else:
                    print(f"            ⚠ No content retrieved")
            
            enriched.append(article)

        # Step 4: Upload to GCS
        print(f"\n[4/4] Uploading to GCS...")
        try:
            blob_path = gcs.upload_topic_results(topic, enriched)
            print(f"      ✅ Uploaded: gs://{gcs.bucket_name}/{blob_path}")
            results_summary.append({"topic": topic, "status": "success", "fetched": len(articles), "passed": len(high_scorers), "saved": len(enriched)})
        except Exception as e:
            print(f"      ❌ Upload failed: {e}")
            results_summary.append({"topic": topic, "status": "upload_failed", "fetched": len(articles), "passed": len(high_scorers), "saved": 0})

    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    total_fetched = sum(r["fetched"] for r in results_summary)
    total_passed = sum(r["passed"] for r in results_summary)
    total_saved = sum(r["saved"] for r in results_summary)
    success = sum(1 for r in results_summary if r["status"] == "success")
    
    print(f"Topics: {len(TOPIC_FOLDERS)} | Successful: {success}")
    print(f"Articles: {total_fetched} fetched → {total_passed} passed → {total_saved} saved")
    print()
    
    for r in results_summary:
        icon = "✅" if r["status"] == "success" else "❌"
        print(f"  {icon} {r['topic']}: {r['fetched']}→{r['passed']}→{r['saved']} ({r['status']})")


if __name__ == "__main__":
    main()
