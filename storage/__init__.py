"""
Storage Package
===============

Google Cloud Storage (GCS) operations and path management for
storing extracted articles, approved articles, and final summaries.

Modules:
    - gcs.py: GCS client wrapper (upload, download, list, delete)
    - paths.py: Consistent GCS path generation helpers

Bucket Structure:
    /raw/{site_id}/{date}/{hash}.md         — Raw extracted articles
    /approved/{site_id}/{date}/{hash}.md    — Articles that passed evaluation
    /summaries/{date}/briefing.md           — Final regulatory briefings
    /archived/{site_id}/{date}/{hash}.md    — Failed/rejected articles
"""
