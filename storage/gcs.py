"""
Google Cloud Storage Operations
================================

Thin wrapper around the GCS Python client for reading and writing
article content and summaries.

Responsibilities:
    - Upload markdown content to a specified GCS path
    - Download markdown content from a specified GCS path
    - List files in a GCS prefix (e.g., all articles for a site on a date)
    - Move/copy files between paths (e.g., raw → approved)
    - Delete files (for cleanup/archival)

Tools:
    - google-cloud-storage: Official GCS Python client

Usage:
    from storage.gcs import upload_content, download_content

    upload_content(
        bucket="regulatory-raw",
        path="raw/42/2026-04-15/abc123.md",
        content="# Article Title\n\nArticle body..."
    )

    content = download_content(
        bucket="regulatory-raw",
        path="raw/42/2026-04-15/abc123.md"
    )

Notes:
    - All GCS operations should include error handling for network
      failures, permission errors, and missing objects.
    - In local development, consider using a GCS emulator or
      falling back to local filesystem storage.
    - Content is stored as UTF-8 encoded plain text (markdown).
"""
