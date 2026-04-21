"""
Metadata Extraction Helpers
============================

Utility functions for extracting article metadata (title, publication
date, author) from raw HTML or markdown content.

Functions:
    extract_title(html: str) -> str | None
        - Tries in order: <meta og:title>, <title>, first <h1>
        - Falls back to None if no title found

    extract_publication_date(html: str) -> datetime | None
        - Tries in order: <meta article:published_time>,
          JSON-LD datePublished, <time> tags, date patterns in text
        - Normalizes to UTC datetime
        - Falls back to None if no date found

    extract_json_ld(html: str) -> dict | None
        - Parses <script type="application/ld+json"> blocks
        - Returns structured data if present (NewsArticle, WebPage, etc.)
        - Useful for enriching metadata from Schema.org markup

Notes:
    - These helpers supplement the metadata that gatherers provide.
      RSS gives rich metadata; Sitemap and ScrapeGraphAI often don't.
    - Date parsing uses dateutil.parser for maximum format flexibility.
    - If the gatherer already provided a title or date, those take
      precedence. These helpers fill in gaps.
"""
