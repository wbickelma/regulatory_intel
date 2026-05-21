"""
Pipeline script that uses DB client to fetch and process articles by topic.

Usage:
    python scripts/run_topics_pipeline.py              # All topics, Gemini only
    python scripts/run_topics_pipeline.py --playwright # All topics, with Playwright
"""
import argparse
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from clients.db_client import DBClient
from clients.gcs_client import GCSClient
from clients.inoreader import InoreaderClient, InoreaderAuthManager
from clients.content_fetcher import fetch_content_with_fallback
from evaluation.scorer import evaluate_articles

# Configuration
DAYS_BACK = 5
RELEVANCE_THRESHOLD = 6


def get_inoreader_client():
    """Initialize Inoreader client with credentials."""
    app_id = os.getenv("CLIENT_ID_INOREADER")
    app_key = os.getenv("CLIENT_SECRET_INOREADER")
    auth_manager = InoreaderAuthManager(app_id=app_id, app_key=app_key)
    return InoreaderClient(app_id=app_id, app_key=app_key, auth_manager=auth_manager)


def main():
    parser = argparse.ArgumentParser(description="Run pipeline for all topics")
    parser.add_argument("--playwright", action="store_true", 
                        help="Enable Playwright for content fetching (default: disabled)")
    args = parser.parse_args()
    
    use_playwright = args.playwright
    
    # Initialize clients
    print("\n[Init] Loading database from GCS...")
    db = DBClient()
    
    # Get all topics from database
    all_topics = db.get_all_topics()
    topic_names = [t.topic_name for t in all_topics]
    
    print("=" * 60)
    print("📊 TOPIC-BASED PIPELINE")
    print(f"   Topics: {len(topic_names)} total")
    print(f"   Days back: {DAYS_BACK}")
    print(f"   Relevance threshold: {RELEVANCE_THRESHOLD}")
    print(f"   Playwright: {'enabled' if use_playwright else 'disabled (Gemini only)'}")
    print("=" * 60)
    
    print("[Init] Connecting to Inoreader...")
    inoreader = get_inoreader_client()
    
    print("[Init] Connecting to GCS...")
    gcs = GCSClient()
    
    results_summary = []
    
    for topic_name in topic_names:
        print("\n" + "=" * 60)
        print(f"📁 {topic_name}")
        print("=" * 60)
        
        # Step 1: Get sources from DB
        print(f"\n[1/5] Getting sources from database...")
        sources = db.get_sources_by_topic(topic_name)
        print(f"      Found {len(sources)} sources")
        
        if not sources:
            print(f"      ⚠ No sources found for topic: {topic_name}")
            results_summary.append({
                "topic": topic_name, 
                "status": "no_sources", 
                "sources": 0
            })
            continue
        
        # Step 2: Fetch articles from each source
        print(f"\n[2/5] Fetching articles from Inoreader...")
        all_articles = []
        
        for source in sources:
            try:
                articles = inoreader.get_folder_articles_sync(
                    folder_name=topic_name,
                    days_back=DAYS_BACK
                )
                all_articles.extend(articles)
                break  # Folder fetch gets all articles, only need once
            except Exception as e:
                print(f"      ⚠ Error fetching from {source.source_name}: {e}")
        
        # Deduplicate by item_id
        seen_ids = set()
        unique_articles = []
        for article in all_articles:
            if article.item_id not in seen_ids:
                seen_ids.add(article.item_id)
                unique_articles.append(article)
        
        print(f"      Found {len(unique_articles)} unique articles")
        
        if not unique_articles:
            print(f"      ⚠ No articles found")
            results_summary.append({
                "topic": topic_name,
                "status": "no_articles",
                "sources": len(sources),
                "articles": 0
            })
            continue
        
        # Step 3: Evaluate articles
        print(f"\n[3/5] Evaluating {len(unique_articles)} articles...")
        evaluate_articles(unique_articles)
        
        high_scorers = []
        for i, article in enumerate(unique_articles, 1):
            score = getattr(article, 'relevance_score', 0)
            action = getattr(article, 'recommended_action', 'none')
            print(f"      [{i}/{len(unique_articles)}] Score: {score}/10 | {article.title[:50]}...")
            
            if score >= RELEVANCE_THRESHOLD:
                high_scorers.append(article)
        
        print(f"      Passed threshold: {len(high_scorers)}/{len(unique_articles)}")
        
        if not high_scorers:
            print(f"      ⚠ No articles passed evaluation")
            results_summary.append({
                "topic": topic_name,
                "status": "none_passed",
                "sources": len(sources),
                "articles": len(unique_articles),
                "passed": 0
            })
            continue
        
        # Step 4: Fetch full content
        print(f"\n[4/5] Fetching full content for {len(high_scorers)} articles...")
        enriched = []
        
        for i, article in enumerate(high_scorers, 1):
            print(f"      [{i}/{len(high_scorers)}] {article.title[:50]}...")
            
            # Try Inoreader mobilizer first
            if not article.full_content or len(article.full_content) < 500:
                try:
                    mobilized = inoreader.get_article_content_sync(article.item_id)
                    if mobilized and len(mobilized) > len(article.full_content or ""):
                        article.full_content = mobilized
                        print(f"            ✓ Mobilizer: {len(mobilized)} chars")
                except Exception as e:
                    print(f"            ⚠ Mobilizer failed: {e}")
            
            # Fallback if still no good content
            if not article.full_content or len(article.full_content) < 500:
                success = fetch_content_with_fallback(article, use_playwright=use_playwright)
                if success:
                    if article.full_content and len(article.full_content) >= 500:
                        print(f"            ✓ Playwright: {len(article.full_content)} chars")
                    elif hasattr(article, 'ai_summary') and article.ai_summary:
                        print(f"            ✓ Gemini Search: {len(article.ai_summary)} chars")
                    else:
                        print(f"            ⚠ No content retrieved")
                else:
                    print(f"            ⚠ No content retrieved")
            
            enriched.append(article)
        
        # Step 5: Upload to GCS
        print(f"\n[5/5] Uploading to GCS...")
        try:
            blob_path = gcs.upload_topic_results(topic_name, enriched)
            print(f"      ✅ Uploaded: gs://{gcs.bucket_name}/{blob_path}")
            results_summary.append({
                "topic": topic_name,
                "status": "success",
                "sources": len(sources),
                "articles": len(unique_articles),
                "passed": len(high_scorers),
                "saved": len(enriched)
            })
        except Exception as e:
            print(f"      ❌ Upload failed: {e}")
            results_summary.append({
                "topic": topic_name,
                "status": "upload_failed",
                "sources": len(sources),
                "articles": len(unique_articles),
                "passed": len(high_scorers),
                "error": str(e)
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    for result in results_summary:
        status_icon = "✅" if result["status"] == "success" else "❌"
        topic = result["topic"]
        status = result["status"]
        
        if status == "success":
            print(f"  {status_icon} {topic}: {result['articles']}→{result['passed']}→{result['saved']}")
        elif status == "no_sources":
            print(f"  {status_icon} {topic}: no sources configured")
        elif status == "no_articles":
            print(f"  {status_icon} {topic}: no articles found")
        elif status == "none_passed":
            print(f"  {status_icon} {topic}: {result['articles']} articles, none passed threshold")
        else:
            print(f"  {status_icon} {topic}: {status}")
    
    print("\n✅ Pipeline complete!")


if __name__ == "__main__":
    main()
