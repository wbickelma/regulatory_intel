"""
ScrapeGraphAI Gatherer
======================

LLM-powered web scraping fallback for sites without RSS feeds
or usable sitemaps.

Responsibilities:
    - Accept a target listing page URL (e.g., sec.gov/news)
    - Use ScrapeGraphAI to intelligently extract article links
      from the page
    - Handle pagination if detectable (page 1, 2, 3...)
    - Return discovered links with whatever metadata ScrapeGraphAI
      can extract (URLs at minimum, titles and dates if available)

Tools:
    - ScrapeGraphAI: LLM-powered scraping framework
    - Configured LLM provider for ScrapeGraphAI's internal use

Input:
    - SiteConfig with strategy=SCRAPEGRAPHAI and target_paths populated

Output:
    - list[DiscoveredLink] with variable metadata (URL always present,
      title and date may or may not be available)

Notes:
    - This is the FALLBACK strategy, used only when RSS and Sitemap
      are not available. It is the least stable and most expensive
      option (requires LLM calls for scraping).
    - Rate limiting is critical — configurable delay between page
      fetches to avoid overloading target sites.
    - ScrapeGraphAI may fail on heavily JavaScript-rendered pages
      or sites with anti-bot protection. Log failures clearly.
    - A confidence check should be applied to the output: if
      ScrapeGraphAI returns zero links or suspiciously few links,
      flag the site for review in monitoring.
"""
