"""
Content Quality Checker
=======================

Validates extracted article content to catch extraction failures
before articles enter the evaluation pipeline.

Checks:
    - Minimum content length (configurable, default: 200 characters)
      Catches empty or near-empty extractions.

    - Login wall detection
      Checks for common login form indicators (password fields,
      "sign in" text patterns) that suggest Crawl4AI hit an
      authentication barrier.

    - Cookie/consent banner detection
      Checks if the extracted text is primarily a cookie consent
      notice rather than article content.

    - Navigation-only detection
      Checks if the content is just a navigation menu or site
      header/footer without actual article text.

Input:
    - content: str — the extracted markdown text
    - metadata: ArticleMetadata

Output:
    - QualityCheckResult: passed (bool), issues (list[str])
    - If failed, the article's status is set to "low_quality"

Notes:
    - Quality checks are intentionally lightweight — heuristic-based,
      no LLM calls. The goal is to catch obvious failures cheaply.
    - Articles that fail quality checks are still stored in GCS
      (for debugging) but are excluded from the evaluation pipeline.
"""
