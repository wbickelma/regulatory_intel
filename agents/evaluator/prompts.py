"""
Evaluator Prompts
=================

Prompt templates for the article evaluation agent.

Prompts:
    EVALUATION_PROMPT
        - Instructs the LLM to evaluate a single article against
          the provided criteria.
        - Specifies the output format (JSON matching EvaluationResult).
        - Includes the evaluation criteria description, document types
          of interest, and jurisdictions of interest.

Template Variables:
    {article_title}       - Title of the article being evaluated
    {article_content}     - Markdown content of the article (possibly truncated)
    {criteria_description} - Human-readable description of what's relevant
    {document_types}      - List of relevant document types
    {jurisdictions}       - List of relevant jurisdictions
    {schema}              - JSON schema of EvaluationResult

Notes:
    - The prompt explicitly instructs the LLM to provide a justification
      for its decision, enabling audit trail functionality.
    - Prompt should emphasize that when uncertain, the LLM should lean
      toward "pass" to avoid missing relevant content (prefer recall
      over precision for regulatory monitoring).
"""
