"""
Summary Schemas
===============

Pydantic models for per-article summaries (map phase) and the
final synthesized regulatory briefing (reduce phase).

Models:
    ArticleSummary
        - Summary of a single article produced during the map phase.
        - Fields: article_id, source_url, title, summary_text,
                  regulatory_action_type, affected_sectors (list[str]),
                  key_dates (list[str]), category

    BriefingSummary
        - Final synthesized regulatory briefing produced during the
          reduce phase.
        - Fields: run_id, run_date, executive_summary (str),
                  sections (list[ArticleSummary]), total_articles_reviewed (int),
                  total_articles_included (int), sites_covered (list[str])

    BriefingSection
        - A single section within the final briefing output.
        - Fields: title, summary_text, source_url, category, publication_date

Usage:
    from schemas.summary import BriefingSummary

    briefing = BriefingSummary(
        run_date="2026-04-15",
        sections=[...],
        executive_summary="This week saw 3 major regulatory updates..."
    )

Output Format:
    The final briefing is rendered as markdown:

    ## Regulatory Update — 2026-04-15

    ### 1. SEC Proposes New Climate Disclosure Requirements
    Summary text...
    **Source:** [SEC Press Release](https://sec.gov/...)
    **Category:** Proposed Rule | **Published:** 2026-04-14

Notes:
    - The map-reduce pattern is used to handle large batches of articles
      without exceeding LLM context window limits.
    - Each section MUST include a source_url linking back to the original.
    - If zero articles pass evaluation, a "No relevant updates" briefing
      is generated.
"""
