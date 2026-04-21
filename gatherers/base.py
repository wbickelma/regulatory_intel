"""
Base Gatherer
=============

Abstract base class that all link discovery gatherers must implement.

Defines the contract:
    - Input: SiteConfig (schemas.site) containing strategy parameters
    - Output: list[DiscoveredLink] (schemas.article)

All gatherers — RSS, Sitemap, ScrapeGraphAI, and any future
additions — implement this interface so the pipeline orchestrator
can treat them interchangeably.

Usage:
    class RSSGatherer(BaseGatherer):
        def gather(self, site_config: SiteConfig) -> list[DiscoveredLink]:
            ...

Notes:
    - Gatherers should handle their own error cases (network failures,
      malformed data) and return an empty list rather than raising
      exceptions, logging the error for monitoring.
    - Gatherers do NOT perform deduplication — that is handled
      separately by dedup.py after gathering.
"""
