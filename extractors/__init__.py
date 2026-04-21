"""
Extractors Package
==================

Content extraction modules responsible for fetching article pages
and extracting their text content as markdown.

Uses Crawl4AI as the primary extraction tool. Extracted content
is stored in Google Cloud Storage as markdown files with
accompanying metadata records in the database.

Modules:
    - crawl4ai.py: Crawl4AI integration for page fetching and text extraction
    - quality_check.py: Content quality validation (min length, login wall detection)
    - metadata.py: Title, date, and metadata extraction helpers
"""
