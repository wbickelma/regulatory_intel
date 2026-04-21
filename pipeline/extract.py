"""
Extract Pipeline
================

Orchestrates content extraction for a batch of discovered links.

Steps:
    1. Accept a list of DiscoveredLinks from the gather phase
    2. For each link:
        a. Fetch and extract content using Crawl4AI (extractors/crawl4ai.py)
        b. Run quality checks (extractors/quality_check.py)
        c. Extract supplementary metadata (extractors/metadata.py)
        d. Store markdown content in GCS (/raw/{site_id}/{date}/{hash}.md)
        e. Write metadata record to articles_raw table
    3. Return list of successfully extracted RawArticles
    4. Log metrics: total attempted, successful, failed, low quality

Input:
    - links: list[DiscoveredLink]
    - site_id: int

Output:
    - list[RawArticle] — successfully extracted articles with content and metadata

Dependencies:
    - extractors.crawl4ai
    - extractors.quality_check
    - extractors.metadata
    - storage.gcs
    - db (articles_raw)

Notes:
    - Extraction is done with configurable concurrency (e.g., max 5
      parallel fetches per site) to respect rate limits.
    - Failed extractions are logged but do not halt the batch.
"""
