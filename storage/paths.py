"""
GCS Path Generation
===================

Helper functions for generating consistent, predictable GCS paths
for stored content.

Functions:
    raw_article_path(site_id: int, date: str, url: str) -> str
        Returns: "raw/{site_id}/{date}/{url_hash}.md"

    approved_article_path(site_id: int, date: str, url: str) -> str
        Returns: "approved/{site_id}/{date}/{url_hash}.md"

    archived_article_path(site_id: int, date: str, url: str) -> str
        Returns: "archived/{site_id}/{date}/{url_hash}.md"

    summary_path(date: str) -> str
        Returns: "summaries/{date}/briefing.md"

    url_hash(url: str) -> str
        Returns: SHA-256 hash of the normalized URL (first 12 chars)

Notes:
    - Consistent path generation ensures articles can be located
      by site_id and date without querying the database.
    - The url_hash function normalizes URLs before hashing to ensure
      the same article always maps to the same filename.
    - Date format is always YYYY-MM-DD.
"""
