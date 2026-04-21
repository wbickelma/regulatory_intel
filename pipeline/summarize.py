"""
Summarize Pipeline
==================

Orchestrates the map-reduce summarization of approved articles
into a final regulatory briefing.

Steps:
    1. Accept a list of approved RawArticles from the evaluate phase
    2. If zero articles → generate "No relevant updates" briefing
    3. MAP PHASE: For each article, invoke the summarizer agent to
       produce an ArticleSummary (agents/summarizer)
    4. REDUCE PHASE: Pass all ArticleSummaries to the summarizer
       agent to produce a synthesized BriefingSummary
    5. Render the briefing as formatted markdown
    6. Store in GCS (/summaries/{date}/briefing.md)
    7. Write record to summaries table in database
    8. Return the BriefingSummary

Input:
    - articles: list[RawArticle] — approved articles with content
    - run_id: str
    - run_date: date

Output:
    - BriefingSummary (schemas.summary)

Dependencies:
    - agents.summarizer
    - storage.gcs
    - db (summaries table)

Notes:
    - For large batches (30+ articles), the reduce phase may need
      to be done in multiple passes to stay within context window limits.
    - Source URLs are preserved through both phases — this is a
      non-negotiable requirement for regulatory traceability.
"""
