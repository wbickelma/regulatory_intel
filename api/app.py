"""
FastAPI Application
===================

Main entry point for the regulatory intelligence API.

Responsibilities:
    - Initialize FastAPI application with OpenAPI metadata
    - Configure CORS middleware
    - Register API routers (sites, runs, summaries)
    - Handle global exceptions and format error responses
    - Define startup/shutdown events (DB connection pooling)

Usage:
    uvicorn api.app:app --host 0.0.0.0 --port 8000
"""
