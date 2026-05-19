#!/usr/bin/env python3
"""
Demo Script
===========

End-to-end demo: onboard a source, fetch articles, evaluate, summarize, and report.
  1. Generate RSS feed for Skadden Insights via RSS.app
  2. Subscribe the feed in Inoreader under test_folder1
  3. Download article metadata from test_folder1 (last N days)
  4. Evaluate each article for relevance to Cisco (via Circuit LLM)
  5. Save scored results to data/ArticleItem_dataclass_example.json
  6. Fetch full content for high-scoring articles (relevance >= 6)
  7. Summarize relevant articles and generate Word doc report
  8. Email report to configured recipients (optional)

Usage:
    python scripts/demo.py
"""
from __future__ import annotations

import json
import os
import sys

# Add project root to path for evaluation import
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from common import (
    DATA_DIR,
    DAYS_BACK,
    load_credentials,
    get_inoreader_client,
    get_rss_client,
)
from evaluation.scorer import evaluate_articles
from summarize import ReportSummarizer
from clients.email_client import EmailClient
from clients.content_fetcher import fetch_content_with_fallback

SOURCE_URL = (
    "https://www.skadden.com/insights"
    "?skip=0&panelid=tab-find-mode&paneltogglestate=2"
    "&type=9cbfe518-3bc0-4632-ae13-6ac9cee8eb31&hassearched=true"
)
TARGET_FOLDER = "test_folder1"
OUTPUT_FILE = os.path.join(DATA_DIR, "demo_feed.json")
EMAIL_RECIPIENTS = os.getenv("REPORT_RECIPIENTS", "").split(",")  # Comma-separated list


def main():
    print("=" * 60)
    print("📡 DEMO — SKADDEN INSIGHTS")
    print("=" * 60)

    creds = load_credentials()
    rss_client = get_rss_client(creds)
    inoreader = get_inoreader_client(creds)

    # --- Step 1: Generate RSS Feed ---
    print(f"\n[STEP 1] Generating RSS feed for:\n  {SOURCE_URL}")
    feed_response = rss_client.create_feed_sync(SOURCE_URL)

    if not feed_response:
        print("❌ Failed to generate RSS feed. Exiting.")
        return

    feed_url = feed_response.feed_url

    # --- Step 2: Subscribe in Inoreader ---
    print(f"\n[STEP 2] Subscribing feed to Inoreader folder '{TARGET_FOLDER}'...")
    inoreader.add_feed_to_folder_sync(feed_url, TARGET_FOLDER)

    # --- Step 3: Fetch articles (metadata only) ---
    print(f"\n[STEP 3] Fetching articles from '{TARGET_FOLDER}' (last {DAYS_BACK} day(s))...")
    articles = inoreader.get_folder_articles_sync(
        TARGET_FOLDER, days_back=DAYS_BACK
    )

    if not articles:
        print("⚠️  No articles found in timeframe.")
        return

    # --- Step 4: Evaluate relevance via Circuit LLM ---
    print(f"\n[STEP 4] Evaluating {len(articles)} articles for Cisco relevance...")
    evaluated_articles = evaluate_articles(articles)

    # --- Step 5: Save results ---
    OUTPUT_FILE = os.path.join(DATA_DIR, "ArticleItem_dataclass_example.json")
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump([a.to_dict() for a in evaluated_articles], f, indent=2, ensure_ascii=False)

    # --- Step 6: Download full content for high scorers (>= 6) ---
    high_scorers = [a for a in evaluated_articles if a.relevance_score is not None and a.relevance_score >= 6]
    
    print(f"\n[STEP 6] Fetching full content for {len(high_scorers)} high-scoring articles (>= 6)...")
    for article in high_scorers:
        print(f"\n{'─' * 60}")
        print(f"📰 {article.title}")
        print(f"🔗 {article.url}")
        
        # Try Inoreader Mobilizer first
        content = inoreader.get_article_content_sync(article.item_id)
        if content:
            plain = inoreader._strip_html(content)
            if plain and len(plain.strip()) >= 100:
                article.full_content = plain
        
        # If Inoreader failed, use fallback chain (modifies article in-place)
        if not article.full_content:
            print("⚠️  Inoreader empty — trying fallback methods...")
            fetch_content_with_fallback(article)
        
        # Show result
        if article.full_content:
            preview = article.full_content[:500] + ("..." if len(article.full_content) > 500 else "")
            print(f"📄 Content preview:\n{preview}")
        elif article.ai_summary:
            preview = article.ai_summary[:500] + ("..." if len(article.ai_summary) > 500 else "")
            print(f"🤖 AI Summary preview:\n{preview}")
        else:
            print("❌ All content fetch methods failed")

    # Re-save with full content included
    if high_scorers:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump([a.to_dict() for a in evaluated_articles], f, indent=2, ensure_ascii=False)

    # --- Summary ---
    scored = [a for a in evaluated_articles if a.relevance_score is not None]
    avg_score = sum(a.relevance_score for a in scored) / len(scored) if scored else 0

    print("\n" + "=" * 60)
    print("📊 DEMO SUMMARY")
    print("=" * 60)
    print(f"Source URL:     {SOURCE_URL}")
    print(f"RSS Feed URL:   {feed_url}")
    print(f"Folder:         {TARGET_FOLDER}")
    print(f"Articles:       {len(evaluated_articles)}")
    print(f"Scored:         {len(scored)}/{len(evaluated_articles)}")
    print(f"Avg Score:      {avg_score:.1f}/10")
    print(f"High Scorers:   {len(high_scorers)} (fetched full content)")
    print(f"Saved to:       {OUTPUT_FILE}")
    print("=" * 60)

    # Top articles by relevance
    if scored:
        print("\n🏆 TOP ARTICLES BY RELEVANCE:")
        for a in sorted(scored, key=lambda x: x.relevance_score, reverse=True)[:5]:
            action = a.evaluation.get("action_needed", "n/a") if a.evaluation else "n/a"
            print(f"  [{a.relevance_score:2d}/10] [{action:>7s}] {a.title}")

    # --- Step 7: Generate Reports (Markdown + Word) ---
    if high_scorers:
        print(f"\n[STEP 7] Generating reports for {len(high_scorers)} high-scoring articles...")
        summarizer = ReportSummarizer()

        # Word document
        docx_path = os.path.join(DATA_DIR, "executive_briefing.docx")
        summarizer.generate_docx(
            high_scorers,
            output_path=docx_path,
            title="Skadden Insights — Executive Briefing"
        )
        print(f"\n📄 Word report saved to: {docx_path}")

        # --- Step 8: Email Report ---
        recipients = [e.strip() for e in EMAIL_RECIPIENTS if e.strip()]
        if recipients:
            print(f"\n[STEP 8] Emailing report to {len(recipients)} recipient(s)...")
            try:
                email_client = EmailClient()
                success = email_client.send_report(
                    to_emails=recipients,
                    subject="Regulatory Intelligence Briefing — Skadden Insights",
                    body_html=f"""
                    <h2>Regulatory Intelligence Briefing</h2>
                    <p>Attached is the executive briefing covering {len(high_scorers)} 
                    high-relevance articles from Skadden Insights.</p>
                    <p><em>Generated automatically by the Regulatory Intelligence system.</em></p>
                    """,
                    attachment_path=docx_path,
                )
                if success:
                    print(f"✅ Email sent to: {', '.join(recipients)}")
                else:
                    print("⚠️  Email send failed")
            except ValueError as e:
                print(f"⚠️  Skipping email: {e}")
        else:
            print("\n[STEP 8] Skipped — no REPORT_RECIPIENTS configured")


if __name__ == "__main__":
    main()
