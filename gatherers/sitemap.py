"""
Sitemap Gatherer
================

Parses Sitemap XML files to discover article URLs.

Responsibilities:
    - Fetch the sitemap XML from the configured sitemap URL
    - Handle sitemap index files (recursively parse child sitemaps)
    - Extract per-entry: URL, lastmod date, changefreq, priority
    - Handle gzipped sitemaps (.xml.gz)
    - Handle large sitemaps efficiently (streaming parser for 50k+ entries)

Tools:
    - xml.etree.ElementTree or lxml: XML parsing
    - httpx or requests: HTTP client for fetching sitemaps
    - gzip: For decompressing gzipped sitemaps

Input:
    - SiteConfig with strategy=SITEMAP and sitemap_url populated

Output:
    - list[DiscoveredLink] with limited metadata (URL, lastmod date only)

Notes:
    - Sitemaps provide URLs and optional lastmod dates but NO titles,
      descriptions, or categories. This metadata must be extracted
      later by Crawl4AI during the content extraction phase.
    - Many government sitemaps include ALL pages on the site, not just
      articles. The target_paths field in SiteConfig can be used to
      filter URLs to only relevant sections (e.g., only URLs matching
      /news/* or /rules/*).
    - If the sitemap URL returns a non-200 status or invalid XML,
      log the error and return an empty list.
"""
