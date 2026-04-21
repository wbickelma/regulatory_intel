"""
Evaluator Agent Core
====================

Evaluates a single article against the configured regulatory
monitoring criteria using an LLM.

Responsibilities:
    - Accept an article's content and metadata
    - Accept the evaluation criteria
    - Construct a prompt that asks the LLM to assess relevance
    - Parse the LLM's response into a structured EvaluationResult
    - Handle long articles (truncation to fit context window)

Tools:
    - LLM provider (OpenAI GPT-4 or equivalent)
    - Pydantic for structured output parsing

Input:
    - article: RawArticle (schemas.article) — content + metadata
    - criteria: EvaluationCriteria (schemas.evaluation)

Output:
    - EvaluationResult (schemas.evaluation)
        - relevance_score: int (1-5)
        - category: str (e.g., "proposed rule", "enforcement action")
        - decision: "pass" or "fail"
        - justification: str (human-readable explanation)

Notes:
    - If article content exceeds the model's context window, truncate
      from the end while preserving the title and opening paragraphs.
    - The LLM is instructed to return JSON matching the EvaluationResult
      schema exactly.
    - Failed LLM calls should be retried up to 3 times with exponential
      backoff before marking the article as "evaluation_failed".
"""
