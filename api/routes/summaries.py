"""
Summaries Router
================

API endpoints for retrieving generated regulatory briefings.

Endpoints:
    GET /summaries
        - List available briefings (metadata only)
        - Returns: list containing date, article_count, sites_included

    GET /summaries/{date}
        - Retrieve the full briefing markdown for a specific date
        - Returns: BriefingSummary
        - Supports a ?format=html query parameter for pre-rendered output.
"""
