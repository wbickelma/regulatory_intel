#!/usr/bin/env python3
"""
Daily Pipeline
==============

Runs the full regulatory intelligence pipeline:
1. Fetch articles from each topic folder (last N days)
2. Evaluate articles for relevance
3. Fetch full content for high-scoring articles (with fallback)
4. Upload results to GCS (one JSON per topic)

Usage:
    python jobs/daily_pipeline.py
    python jobs/daily_pipeline.py --days-back 2
    python jobs/daily_pipeline.py --dry-run  # Skip GCS upload
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from clients.inoreader import ArticleItem
from clients.content_fetcher import fetch_content_with_fallback
from config.settings import settings, TOPIC_FOLDERS
from config.logging_config import setup_logging
from evaluation.scorer import evaluate_articles
from scripts.common import load_credentials, get_inoreader_client

logger = logging.getLogger(__name__)


def process_topic(
    topic: str,
    inoreader,
    days_back: int,
    relevance_threshold: int,
) -> List[ArticleItem]:
    """Process a single topic folder.
    
    Returns:
        List of articles that passed evaluation and have content.
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"📁 Processing topic: {topic}")
    logger.info(f"{'='*60}")
    
    # Step 1: Fetch articles
    logger.info(f"[1/3] Fetching articles (last {days_back} days)...")
    try:
        articles = inoreader.get_folder_articles_sync(topic, days_back=days_back)
    except Exception as e:
        logger.error(f"Failed to fetch articles for {topic}: {e}")
        return []
    
    if not articles:
        logger.info(f"No articles found for {topic}")
        return []
    
    logger.info(f"Found {len(articles)} articles")
    
    # Step 2: Evaluate articles
    logger.info(f"[2/3] Evaluating {len(articles)} articles...")
    evaluated = evaluate_articles(articles)
    
    # Filter by relevance threshold
    high_scorers = [
        a for a in evaluated
        if a.relevance_score is not None and a.relevance_score >= relevance_threshold
    ]
    logger.info(f"📊 {len(high_scorers)}/{len(articles)} articles passed threshold (>= {relevance_threshold})")
    
    if not high_scorers:
        return []
    
    # Step 3: Fetch full content
    logger.info(f"[3/3] Fetching full content for {len(high_scorers)} articles...")
    articles_with_content = []
    
    for i, article in enumerate(high_scorers, 1):
        logger.info(f"  [{i}/{len(high_scorers)}] {article.title[:50]}...")
        
        # Try Inoreader Mobilizer first
        content = inoreader.get_article_content_sync(article.item_id)
        if content:
            plain = inoreader._strip_html(content)
            if plain and len(plain.strip()) >= 100:
                article.full_content = plain
                articles_with_content.append(article)
                logger.info(f"    ✅ Inoreader ({len(plain)} chars)")
                continue
        
        # Use fallback chain
        logger.info(f"    ⚠️  Inoreader empty, trying fallback...")
        success = fetch_content_with_fallback(article)
        
        if article.full_content or article.ai_summary:
            articles_with_content.append(article)
            method = "full_content" if article.full_content else "ai_summary"
            length = len(article.full_content or article.ai_summary or "")
            logger.info(f"    ✅ Fallback ({method}, {length} chars)")
        else:
            logger.warning(f"    ❌ All methods failed")
    
    logger.info(f"✅ {len(articles_with_content)} articles with content for {topic}")
    return articles_with_content


def run_pipeline(
    days_back: int = None,
    relevance_threshold: int = None,
    topics: List[str] = None,
    dry_run: bool = False,
) -> dict:
    """Run the full daily pipeline.
    
    Args:
        days_back: Days of articles to process
        relevance_threshold: Minimum score to fetch content
        topics: List of topic folders (defaults to TOPIC_FOLDERS)
        dry_run: If True, skip GCS upload
        
    Returns:
        Summary dict with statistics
    """
    days_back = days_back or settings.days_back
    relevance_threshold = relevance_threshold or settings.relevance_threshold
    topics = topics or TOPIC_FOLDERS
    
    logger.info("=" * 70)
    logger.info("🚀 DAILY REGULATORY INTELLIGENCE PIPELINE")
    logger.info("=" * 70)
    logger.info(f"Topics: {len(topics)}")
    logger.info(f"Days back: {days_back}")
    logger.info(f"Relevance threshold: {relevance_threshold}")
    logger.info(f"Dry run: {dry_run}")
    
    # Initialize clients
    creds = load_credentials()
    inoreader = get_inoreader_client(creds)
    
    if not dry_run:
        from clients.gcs_client import GCSClient
        gcs = GCSClient()
    
    # Process each topic
    summary = {
        "run_date": datetime.utcnow().isoformat(),
        "days_back": days_back,
        "relevance_threshold": relevance_threshold,
        "topics": {},
    }
    
    total_fetched = 0
    total_passed = 0
    total_with_content = 0
    
    for topic in topics:
        try:
            articles = process_topic(
                topic=topic,
                inoreader=inoreader,
                days_back=days_back,
                relevance_threshold=relevance_threshold,
            )
            
            # Upload to GCS
            if articles and not dry_run:
                gcs_path = gcs.upload_topic_results(topic, articles)
                logger.info(f"📤 Uploaded to {gcs_path}")
            
            summary["topics"][topic] = {
                "articles_with_content": len(articles),
                "uploaded": not dry_run and len(articles) > 0,
            }
            total_with_content += len(articles)
            
        except Exception as e:
            logger.error(f"Failed processing topic {topic}: {e}")
            summary["topics"][topic] = {"error": str(e)}
    
    # Upload daily summary
    summary["total_articles_with_content"] = total_with_content
    
    if not dry_run:
        gcs.upload_daily_summary(summary)
    
    # Final summary
    logger.info("\n" + "=" * 70)
    logger.info("📊 PIPELINE COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Topics processed: {len(topics)}")
    logger.info(f"Total articles with content: {total_with_content}")
    
    return summary


def main():
    parser = argparse.ArgumentParser(description="Run daily regulatory intelligence pipeline")
    parser.add_argument("--days-back", type=int, help="Days of articles to process")
    parser.add_argument("--threshold", type=int, help="Minimum relevance score")
    parser.add_argument("--topics", nargs="+", help="Specific topics to process")
    parser.add_argument("--dry-run", action="store_true", help="Skip GCS upload")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Setup logging
    log_level = "DEBUG" if args.debug else settings.log_level
    setup_logging(log_level)
    
    # Run pipeline
    summary = run_pipeline(
        days_back=args.days_back,
        relevance_threshold=args.threshold,
        topics=args.topics,
        dry_run=args.dry_run,
    )
    
    # Print summary
    print("\n" + json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
