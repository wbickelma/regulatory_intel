"""
Gatherers Package
=================

Link discovery modules responsible for finding new article URLs
from configured sources. Gatherers are pure data engineering — they
parse structured feeds and documents without using LLMs (except
ScrapeGraphAI, which uses LLM-powered scraping as a fallback).

All gatherers implement the BaseGatherer interface and return a
list of DiscoveredLink objects.

Modules:
    - base.py: Abstract base class defining the gatherer interface
    - rss.py: RSS/Atom feed parser
    - sitemap.py: Sitemap XML parser
    - scrapegraphai.py: LLM-powered web scraping fallback
    - dedup.py: Deduplication engine (checks seen_links table)

Strategy Priority:
    1. RSS (most reliable, richest metadata)
    2. Sitemap (good coverage, limited metadata)
    3. ScrapeGraphAI (fallback, least stable)

The pipeline/gather.py orchestrator selects the correct gatherer
based on the site's stored configuration.
"""
