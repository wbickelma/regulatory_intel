"""
Gather Pipeline
===============

Orchestrates link discovery for a single site based on its
stored configuration.

Steps:
    1. Load the site's SiteConfig from the database
    2. Instantiate the correct gatherer based on strategy:
        - RSS → RSSGatherer
        - SITEMAP → SitemapGatherer
        - SCRAPEGRAPHAI → ScrapeGraphAIGatherer
    3. Execute the gatherer to discover links
    4. Run deduplication (gatherers/dedup.py) to filter out seen links
    5. Apply date filtering (only links within configured window)
    6. Return list of new, unseen DiscoveredLinks
    7. Log metrics: total discovered, duplicates skipped, new links

Input:
    - site_id: int
    - date_from: datetime (optional, for date filtering)

Output:
    - list[DiscoveredLink] — new links ready for extraction

Dependencies:
    - gatherers.rss / gatherers.sitemap / gatherers.scrapegraphai
    - gatherers.dedup
    - db (site_configs, seen_links)
"""
