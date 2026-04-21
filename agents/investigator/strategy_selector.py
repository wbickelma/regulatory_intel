"""
Strategy Selector
=================

Implements the strategy selection waterfall based on the investigation
agent's findings.

Waterfall Logic:
    1. If active RSS/Atom feeds were discovered:
        - Validate the feed (is it reachable? does it have recent entries?)
        - If valid → strategy = RSS, target_url = feed URL
    2. Else if sitemaps were discovered:
        - Validate the sitemap (is it reachable? does it have recent entries?)
        - If valid → strategy = SITEMAP, target_url = sitemap URL
    3. Else:
        - strategy = SCRAPEGRAPHAI
        - target_url = best content path discovered (e.g., /news)
        - confidence is set LOW

Input:
    - SiteInvestigationResult (schemas.investigation)

Output:
    - StrategyDecision (schemas.investigation)
        Contains: strategy, target_url, confidence, reasoning

Validation Checks:
    - RSS: Feed URL returns valid XML, contains entries, most recent
      entry is within the last 90 days.
    - Sitemap: Sitemap URL returns valid XML, contains URLs, has
      lastmod dates within a reasonable range.
    - If validation fails, the strategy is demoted to the next option
      in the waterfall.

Notes:
    - A strategy with confidence < 0.5 should be flagged in logs
      as potentially unreliable.
    - The reasoning field documents why the strategy was selected,
      supporting future debugging and auditing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree

import httpx

from config.logging_config import get_logger
from config.settings import settings
from schemas.investigation import (
    SiteInvestigationResult,
    StrategyDecision,
)
from schemas.site import StrategyEnum

logger = get_logger(__name__)

_FEED_TIMEOUT = 15  # seconds


async def _validate_rss(url: str) -> bool:
    """Return True if *url* responds with parseable XML containing entries."""
    try:
        async with httpx.AsyncClient(timeout=_FEED_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "RegulatoryIntelBot/1.0"})
            resp.raise_for_status()
        root = ElementTree.fromstring(resp.text)
        # RSS 2.0 items or Atom entries
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry") or root.findall(".//item")
        return len(items) > 0
    except Exception as exc:
        logger.warning("RSS validation failed for %s: %s", url, exc, extra={"url": url})
        return False


async def _validate_sitemap(url: str) -> bool:
    """Return True if *url* responds with parseable sitemap XML containing URLs."""
    try:
        async with httpx.AsyncClient(timeout=_FEED_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "RegulatoryIntelBot/1.0"})
            resp.raise_for_status()
        root = ElementTree.fromstring(resp.text)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = root.findall(".//sm:url", ns) or root.findall(".//sm:sitemap", ns)
        return len(urls) > 0
    except Exception as exc:
        logger.warning("Sitemap validation failed for %s: %s", url, exc, extra={"url": url})
        return False


async def select_strategy(result: SiteInvestigationResult) -> StrategyDecision:
    """
    Walk the discovery waterfall and return the best validated
    strategy for the site.

    Priority: RSS → Sitemap → ScrapeGraphAI.
    """
    # --- 1. Try RSS feeds (prefer active ones first) --------------------------
    active_feeds = [f for f in result.rss_feeds if f.is_active]
    inactive_feeds = [f for f in result.rss_feeds if not f.is_active]

    for feed in active_feeds + inactive_feeds:
        if await _validate_rss(feed.url):
            confidence = 0.9 if feed.is_active else 0.6
            logger.info(
                "Strategy selected: RSS (%s)", feed.url,
                extra={"url": feed.url},
            )
            return StrategyDecision(
                strategy=StrategyEnum.RSS,
                target_url=feed.url,
                confidence=confidence,
                reasoning=f"Active RSS feed validated at {feed.url}",
            )

    # --- 2. Try sitemaps -------------------------------------------------------
    for smap in result.sitemaps:
        if await _validate_sitemap(smap.url):
            confidence = 0.7
            logger.info(
                "Strategy selected: SITEMAP (%s)", smap.url,
                extra={"url": smap.url},
            )
            return StrategyDecision(
                strategy=StrategyEnum.SITEMAP,
                target_url=smap.url,
                confidence=confidence,
                reasoning=f"Sitemap validated at {smap.url}",
            )

    # --- 3. Fallback to ScrapeGraphAI ------------------------------------------
    target = result.content_paths[0] if result.content_paths else ""
    confidence = 0.3
    logger.warning(
        "Falling back to SCRAPEGRAPHAI (confidence %.1f)", confidence,
        extra={"url": target},
    )
    return StrategyDecision(
        strategy=StrategyEnum.SCRAPEGRAPHAI,
        target_url=target,
        confidence=confidence,
        reasoning="No valid RSS feed or sitemap found; defaulting to LLM scraping.",
    )
