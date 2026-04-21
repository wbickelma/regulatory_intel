"""
Agents Package
==============

LLM-powered agents that provide the intelligence layer of the
regulatory news summarizer. Each agent handles a distinct cognitive
task in the pipeline.

Agents:
    investigator/
        - Probes new websites to discover ingestion methods (RSS, Sitemap, etc.)
        - Uses GPT Researcher for autonomous web investigation
        - Outputs structured SiteInvestigationResult via Pydantic

    evaluator/
        - Assesses each extracted article against configured criteria
        - Scores relevance, assigns categories, provides justification
        - Outputs structured EvaluationResult via Pydantic

    summarizer/
        - Produces concise summaries of approved regulatory articles
        - Uses map-reduce pattern: per-article summaries → synthesized briefing
        - Outputs structured BriefingSummary via Pydantic

Design Principles:
    - All agents return structured Pydantic models, never raw strings.
    - Prompts are isolated in dedicated prompts.py files for easy iteration.
    - Agents are stateless — all context is passed in, all output is returned.
    - Agent modules do NOT access the database directly. They receive
      input and return output; the pipeline layer handles persistence.
"""
