"""
Schemas Package
===============

Pydantic models that serve as the data contracts across the entire
application. Every module — agents, gatherers, extractors, pipeline,
and API — imports from this package to ensure consistent data shapes.

Modules:
    - site: Models for site registration and configuration
    - investigation: Models for GPT Researcher output and strategy selection
    - article: Models for discovered links and extracted article content
    - evaluation: Models for evaluation criteria and LLM evaluation results
    - summary: Models for per-article and final briefing summaries

Design Principles:
    - All inter-module data exchange uses these Pydantic models.
    - Models include validation rules to catch malformed data early.
    - Serialization to/from JSON is used for GCS storage and API responses.
"""
