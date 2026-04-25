"""Weekly report generation job.

This module is the entrypoint for the scheduled weekly report.
Triggered by Cloud Scheduler via HTTP or Pub/Sub.
"""

import asyncio
import logging
from datetime import datetime

from config.settings import get_settings
from db.session import get_db
from clients import RssAppClient, InoreaderClient, GeminiClient
from services import (
    FeedManager,
    ArticleExtractor,
    RelevanceClassifier,
    ReportGenerator
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_weekly_report(days: int = 7) -> str:
    """Execute the weekly report generation pipeline.
    
    Args:
        days: Number of days to look back (default: 7).
        
    Returns:
        Report ID as string.
    """
    settings = get_settings()
    db = next(get_db())
    
    logger.info(f"Starting weekly report generation for past {days} days")
    start_time = datetime.utcnow()
    
    try:
        async with RssAppClient(settings.rssapp_api_key) as rss_client:
            async with InoreaderClient(
                settings.inoreader_api_key,
                settings.inoreader_app_id
            ) as inoreader_client:
                gemini_client = GeminiClient(settings.gemini_api_key)
                
                extractor = ArticleExtractor(db, inoreader_client)
                classifier = RelevanceClassifier(db, gemini_client)
                
                generator = ReportGenerator(
                    db=db,
                    extractor=extractor,
                    classifier=classifier,
                    llm_client=gemini_client
                )
                
                report = await generator.generate_report(topic_id=None, days=days)
                
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                logger.info(
                    f"Report generated: {report.id} | "
                    f"Articles: {report.article_count} | "
                    f"Duration: {elapsed:.1f}s"
                )
                
                return str(report.id)
                
    except Exception as e:
        logger.error(f"Weekly report failed: {e}", exc_info=True)
        raise


def main():
    """CLI entrypoint for manual execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate weekly regulatory report")
    parser.add_argument("--days", type=int, default=7, help="Days to look back")
    args = parser.parse_args()
    
    report_id = asyncio.run(run_weekly_report(args.days))
    print(f"Report generated: {report_id}")


if __name__ == "__main__":
    main()
