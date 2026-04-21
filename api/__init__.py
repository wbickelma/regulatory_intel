"""
API Package
===========

FastAPI web application providing HTTP endpoints for the
regulatory news summarizer.

Modules:
    - app.py: FastAPI application initialization and middleware
    - routes/: Endpoint definitions organized by resource
    - dependencies.py: Shared FastAPI dependencies (DB sessions, etc.)

Endpoints:
    Sites:
        POST   /sites          - Onboard a new website
        GET    /sites          - List all onboarded sites
        GET    /sites/{id}     - Get site details and config

    Runs:
        POST   /runs           - Trigger a pipeline run
        GET    /runs/{id}      - Get run status and metrics

    Summaries:
        GET    /summaries              - List all generated briefings
        GET    /summaries/{date}       - Get briefing for a specific date
"""
