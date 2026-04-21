"""
Crawl4AI Extractor
==================

Fetches article pages and extracts their main content as markdown
using Crawl4AI.

Responsibilities:
    - Accept a DiscoveredLink (URL + optional metadata)
    - Fetch the page using Crawl4AI's browser automation
    - Extract the main article body as clean markdown
    - Extract page title from <title>, <h1>, or meta tags
    - Extract publication date from meta tags, JSON-LD, or visible text
    - Return a RawArticle with content and metadata

Tools:
    - Crawl4AI: LLM-optimized web content extraction
    - Configured with headless browser, appropriate user-agent

Input:
    - link: DiscoveredLink (schemas.article)
    - site_id: int

Output:
    - RawArticle (schemas.article) — markdown content + metadata

Configuration:
    - Headless browser mode (always)
    - Configurable timeout per page (default: 30 seconds)
    - Configurable retry count (default: 3 with exponential backoff)
    - User-agent string (configurable, respectful identification)

Notes:
    - Crawl4AI handles JavaScript rendering, which is critical for
      modern government sites.
    - If extraction fails after retries, return a RawArticle with
      status="failed" and empty content.
    - For batch processing, implement concurrency with a configurable
      max-parallelism cap to avoid overwhelming target sites.
"""
