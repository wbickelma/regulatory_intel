"""
Deduplication Engine
====================

Filters out previously seen URLs from a batch of discovered links
to prevent reprocessing articles on subsequent pipeline runs.

Responsibilities:
    - Accept a list of DiscoveredLink objects from a gatherer
    - Check each URL against the seen_links table in the database
    - Return only links that have NOT been seen before
    - Insert newly seen links into the seen_links table
    - Update last_seen timestamp for links that were rediscovered

Tools:
    - SQLAlchemy (via db.engine) for seen_links table queries
    - hashlib for consistent URL hashing

Input:
    - links: list[DiscoveredLink] — raw output from a gatherer
    - site_id: int — the site these links belong to

Output:
    - list[DiscoveredLink] — only the NEW, unseen links

URL Normalization:
    - Strips trailing slashes
    - Normalizes http vs https
    - Removes common tracking query parameters (utm_*, ref, etc.)
    - Lowercases the domain portion
    - Hashes the normalized URL for storage and lookup

Notes:
    - Deduplication runs AFTER gathering and BEFORE extraction,
      ensuring Crawl4AI only processes genuinely new content.
    - The seen_links table grows over time. Consider periodic
      cleanup of entries older than N days for inactive sites.
"""
