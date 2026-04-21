"""
ORM Models
==========

SQLAlchemy ORM model definitions for all database tables.

Tables:
    Site
        - id, url, domain, jurisdiction, status, created_by, created_at,
          expected_update_frequency
        - Represents a registered website submitted for monitoring.

    SiteConfig
        - id, site_id (FK), strategy (RSS/SITEMAP/SCRAPEGRAPHAI),
          feed_url, sitemap_url, target_paths, confidence_score,
          version, approved_at
        - Stores the selected ingestion strategy and its parameters.
          Versioned to support re-onboarding when sites change.

    SeenLink
        - url_hash (PK), url, site_id (FK), first_seen, last_seen
        - Deduplication table. Tracks every URL discovered to prevent
          reprocessing on subsequent pipeline runs.

    ArticleRaw
        - id, site_id (FK), source_url, title, publication_date,
          extraction_timestamp, content_path (GCS), content_length, status
        - Metadata record for each extracted article. The actual markdown
          content is stored in Google Cloud Storage; this table holds
          the pointer and metadata.

    Evaluation
        - id, article_id (FK), relevance_score (1-5), category,
          decision (pass/maybe/fail), justification, evaluated_at
        - Stores the evaluator LLM's assessment of each article.

    Summary
        - id, run_id, run_date, content, sites_included,
          article_count, created_at
        - Stores the final generated regulatory briefing.

Dependencies:
    - SQLAlchemy
    - db.engine (Base declarative class)
"""
