"""
Runs Router
===========

API endpoints for managing pipeline runs.

Endpoints:
    POST /runs
        - Triggers an immediate pipeline run (can specify single site_id)
        - Returns: run_id and status="started"
        - Note: Should trigger a background task, returning 202 Accepted.

    GET /runs/{run_id}
        - Get the status and metrics of a specific run
        - Returns: phase (gathering, extracting...), metrics dict
"""
