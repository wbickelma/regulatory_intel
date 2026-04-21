"""
Summarizer Prompts
==================

Prompt templates for the map and reduce phases of summarization.

Prompts:
    MAP_PROMPT
        - Instructs the LLM to summarize a single regulatory article.
        - Specifies output format (JSON matching ArticleSummary).
        - Emphasizes extracting: key regulatory action, affected parties,
          deadlines, and preserving the source URL.

    REDUCE_PROMPT
        - Instructs the LLM to synthesize multiple ArticleSummaries
          into a cohesive BriefingSummary.
        - Specifies grouping (by category or jurisdiction).
        - Requires an executive summary at the top.
        - Each section must include the source URL.
        - Specifies output format (JSON matching BriefingSummary).

    NO_RESULTS_TEMPLATE
        - Static template used when zero articles pass evaluation.
        - Generates a "No relevant updates found" briefing.

Template Variables:
    MAP_PROMPT:
        {article_title}    - Title of the article
        {article_content}  - Markdown content (possibly truncated)
        {source_url}       - Original article URL
        {schema}           - JSON schema of ArticleSummary

    REDUCE_PROMPT:
        {article_summaries} - JSON array of ArticleSummary objects
        {run_date}          - Date of this pipeline run
        {schema}            - JSON schema of BriefingSummary

Notes:
    - The reduce prompt must explicitly instruct the LLM to NOT
      discard source URLs during synthesis.
    - For large batches, article_summaries in the reduce prompt may
      need to be chunked into multiple reduce passes.
"""
