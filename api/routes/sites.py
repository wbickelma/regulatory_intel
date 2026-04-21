"""
Sites Router
============

API endpoints for managing monitored websites.

Endpoints:
    POST /sites
        - Trigger the onboarding pipeline for a new URL
        - Returns: The assigned site_id and initial status

    GET /sites
        - List all configured sites
        - Returns: list[SiteRecord]

    GET /sites/{site_id}
        - Get full details for a site, including its active SiteConfig
        - Returns: SiteRecord + SiteConfig

    PUT /sites/{site_id}/status
        - Toggle site monitoring (active/paused)
        - Returns: Updated SiteRecord
"""
