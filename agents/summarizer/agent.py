"""
Summarizer Agent Core
=====================

Produces regulatory briefings from approved articles using a
map-reduce summarization pattern.

Map Phase:
    - For each approved article, generate an ArticleSummary:
        * 2-4 sentence summary of key regulatory points
        * Regulatory action type (proposed rule, final rule, guidance, etc.)
        * Affected sectors and parties
        * Key dates or deadlines mentioned
        * Source URL preserved for attribution

Reduce Phase:
    - Combine all ArticleSummaries into a single BriefingSummary:
        * Executive summary (2-3 sentences covering all updates)
        * Sections grouped by category or jurisdiction
        * Each section links back to original source URL
        * Total article counts and sites covered

Tools:
    - LLM provider (OpenAI GPT-4 or equivalent)
    - Pydantic for structured output parsing

Input:
    - articles: list[RawArticle] — approved articles with content and metadata

Output:
    - BriefingSummary (schemas.summary)

Notes:
    - The map-reduce pattern avoids context window overflow when
      processing large batches (e.g., 50+ articles in a single run).
    - If zero articles are provided, the agent returns a BriefingSummary
      with executive_summary = "No relevant regulatory updates found
      for this period."
    - Source URLs MUST be preserved through both phases — this is a
      hard requirement for regulatory traceability.
"""
