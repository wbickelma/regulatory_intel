"""
Evaluation Schemas
==================

Pydantic models for evaluation criteria configuration and the
evaluator LLM's structured output.

Models:
    EvaluationCriteria
        - Defines what the evaluator LLM should look for.
        - Fields: description (str), document_types (list[str]),
                  jurisdictions (list[str]), relevance_threshold (int)
        - Stored in the database and versioned. Passed to the evaluator
          LLM as part of the evaluation prompt.

    EvaluationResult
        - Structured output from the evaluator LLM for a single article.
        - Fields: article_id, relevance_score (1-5), category (str),
                  decision (pass/fail), justification (str)
        - The justification field provides an audit trail explaining
          why the article was included or excluded.

Usage:
    from schemas.evaluation import EvaluationResult

    result = EvaluationResult(
        article_id=42,
        relevance_score=4,
        category="proposed rule",
        decision="pass",
        justification="Article describes a new SEC proposed rule on..."
    )

Notes:
    - decision is one of: "pass", "fail".
    - relevance_score >= relevance_threshold → pass.
    - The evaluator prompt instructs the LLM to return JSON matching
      EvaluationResult exactly.
"""
