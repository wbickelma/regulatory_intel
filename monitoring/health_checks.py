"""
Health Checks
=============

Verifies connectivity and health of critical external dependencies.

Checks:
    - Database Connectivity: Can we ping Cloud SQL?
    - GCS Access: Can we list objects in the configured buckets?
    - LLM Provider: Is the OpenAI API reachable and returning valid shapes?

Usage:
    Can be exposed via a GET /healthz endpoint for Cloud Run
    liveness probes.
"""
