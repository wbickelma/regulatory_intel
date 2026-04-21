"""
RSS Gatherer
============

Parses RSS and Atom feeds to discover article links.

Responsibilities:
    - Fetch the RSS/Atom feed XML from the configured feed URL
    - Parse feed entries using the feedparser library
    - Extract per-entry: URL, title, publication date, description
    - Normalize dates to ISO 8601 format
    - Handle common feed variations (RSS 2.0, Atom, RDF)
    - Handle malformed feeds gracefully (partial parsing)

Tools:
    - feedparser: Universal RSS/Atom feed parser
    - httpx or requests: HTTP client for fetching feeds

Input:
    - SiteConfig with strategy=RSS and feed_url populated

Output:
    - list[DiscoveredLink] with rich metadata (title, date, description)

Notes:
    - RSS is the preferred strategy because it provides the richest
      metadata per entry, reducing reliance on the extraction phase
      for title and date information.
    - If the feed URL returns a non-200 status or invalid XML,
      log the error and return an empty list.
    - Date formats in RSS feeds vary wildly. Use dateutil.parser
      for robust date parsing.
"""
