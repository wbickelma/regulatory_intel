"""
Article Schemas
===============

Pydantic models for discovered links and extracted article content.

Models:
    DiscoveredLink
        - A URL discovered by a gatherer (RSS, Sitemap, or ScrapeGraphAI).
        - Fields: url, title (optional), publication_date (optional),
                  source_strategy (RSS/SITEMAP/SCRAPEGRAPHAI)
        - Note: RSS provides rich metadata; Sitemap and ScrapeGraphAI
                may only provide the URL and possibly a date.

    ArticleMetadata
        - Metadata extracted alongside article content.
        - Fields: source_url, title, publication_date, extraction_timestamp,
                  site_id, content_path (GCS), content_length, status

    RawArticle
        - Full extracted article including content and metadata.
        - Fields: metadata (ArticleMetadata), content (str — markdown text)

Usage:
    from schemas.article import DiscoveredLink, RawArticle

    link = DiscoveredLink(url="https://sec.gov/news/press-release/2026-42")
    article = RawArticle(metadata=metadata, content=markdown_text)

Notes:
    - content is the markdown text body, NOT stored in the database.
      It lives in GCS at the path specified by metadata.content_path.
    - status is one of: "extracted", "failed", "low_quality".
"""
