"""
Evaluate Pipeline
=================

Orchestrates LLM evaluation for a batch of extracted articles.

Steps:
    1. Accept a list of RawArticles from the extract phase
    2. Load the evaluation criteria from the database
    3. For each article:
        a. Send to the evaluator agent (agents/evaluator)
        b. Receive structured EvaluationResult
        c. Route based on decision:
            - "pass" → copy to /approved/ in GCS, update DB status
            - "fail" → move to /archived/ in GCS, update DB status
        d. Store EvaluationResult in evaluations table
    4. Return list of approved RawArticles
    5. Log metrics: total evaluated, passed, failed

Input:
    - articles: list[RawArticle]

Output:
    - list[RawArticle] — only articles that passed evaluation

Dependencies:
    - agents.evaluator
    - storage.gcs (for moving files between raw/approved/archived)
    - db (evaluations table, articles_raw status update)
"""
