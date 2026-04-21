"""
Evaluator Agent
===============

Responsible for assessing whether extracted articles are relevant
to the user's regulatory monitoring criteria.

Tools:
    - LLM (OpenAI or equivalent) for relevance assessment
    - Pydantic for structured output parsing

Modules:
    - agent.py: Core evaluation logic and LLM orchestration
    - prompts.py: Evaluation prompt templates

Input:
    - Article content (markdown text) and metadata
    - EvaluationCriteria (schemas.evaluation) defining what to look for

Output:
    - EvaluationResult (schemas.evaluation) per article
        Contains: relevance_score (1-5), category, decision (pass/fail),
        justification
"""
