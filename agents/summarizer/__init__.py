"""
Summarizer Agent
================

Responsible for producing concise, source-linked summaries of
approved regulatory articles.

Uses a map-reduce pattern:
    MAP PHASE:    Each article → individual ArticleSummary
    REDUCE PHASE: All ArticleSummaries → single BriefingSummary

Tools:
    - LLM (OpenAI or equivalent) for summarization
    - Pydantic for structured output parsing

Modules:
    - agent.py: Core summarization logic (map and reduce phases)
    - prompts.py: Summarization prompt templates

Input:
    - List of approved RawArticle objects (content + metadata)

Output:
    - BriefingSummary (schemas.summary)
        Contains: executive_summary, list of BriefingSections each
        with summary text and source URL, total counts
"""
