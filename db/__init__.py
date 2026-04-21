"""
Database Package
================

Database engine, ORM models, and migration management for the
regulatory news summarizer.

Uses SQLAlchemy as the ORM and Alembic for schema migrations.
The database is hosted on Google Cloud SQL (PostgreSQL).

Modules:
    - engine: SQLAlchemy engine and session factory
    - models: ORM table definitions (sites, site_configs, seen_links,
              articles_raw, evaluations, summaries)
    - migrations/: Alembic migration scripts

Tables:
    - sites: Registered websites submitted by users
    - site_configs: Strategy configuration per site (RSS, Sitemap, ScrapeGraphAI)
    - seen_links: Deduplication tracking for discovered URLs
    - articles_raw: Metadata for extracted articles (content stored in GCS)
    - evaluations: LLM evaluation results per article
    - summaries: Final generated briefings
"""
