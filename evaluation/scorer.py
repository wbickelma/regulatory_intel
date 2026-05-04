"""Article relevance scorer using Circuit LLM.

Uses the evaluation_scoring.txt prompt template to score articles
on a 0-10 scale for relevance to Cisco's business and regulatory interests.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from langchain_openai import AzureChatOpenAI

from .circuit_client import CircuitClient

from clients.inoreader import ArticleItem

logger = logging.getLogger(__name__)

# Resolve paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent
PROMPT_PATH = PROJECT_ROOT / "prompts" / "evaluation_scoring.txt"


def _load_prompt_template() -> str:
    """Load the evaluation prompt template from disk."""
    return PROMPT_PATH.read_text(encoding="utf-8")


def evaluate_article(
    article: ArticleItem,
    llm: AzureChatOpenAI,
    prompt_template: str | None = None,
) -> dict:
    """Score a single article for relevance to Cisco.

    Args:
        article: ArticleItem dataclass instance.
        llm: A LangChain AzureChatOpenAI instance.
        prompt_template: Optional override for the prompt template string.

    Returns:
        Dict with relevance_score (0-10), reasoning, primary_domain,
        cisco_business_areas, and action_needed.
    """
    template = prompt_template or _load_prompt_template()

    # Use summary as fallback content when full_content is empty
    content_for_eval = article.full_content or article.summary or ""

    prompt = template.format(
        title=article.title or "",
        url=article.url or "",
        published_at=article.published_at.isoformat() if article.published_at else "",
        summary=article.summary or "",
        full_content=content_for_eval,
    )

    response = llm.invoke(prompt)
    raw = response.content.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse LLM response as JSON: {raw[:200]}")
        result = {
            "relevance_score": 0,
            "reasoning": f"Parse error. Raw response: {raw[:300]}",
            "primary_domain": "unknown",
            "cisco_business_areas": [],
            "action_needed": "review",
        }

    # Clamp score to 0-10
    score = result.get("relevance_score", 0)
    if isinstance(score, (int, float)):
        result["relevance_score"] = max(0, min(10, int(score)))

    return result


def evaluate_articles(
    articles: list[ArticleItem],
    llm: AzureChatOpenAI | None = None,
) -> list[ArticleItem]:
    """Score a list of articles, mutating each with evaluation results.

    Args:
        articles: List of ArticleItem instances.
        llm: Optional pre-built LLM; creates one via CircuitClient if omitted.

    Returns:
        The same list with relevance_score and evaluation fields populated.
    """
    if llm is None:
        circuit = CircuitClient()
        llm = circuit.get_llm()

    template = _load_prompt_template()

    for i, article in enumerate(articles, 1):
        title = article.title or "untitled"
        print(f"\n[{i}/{len(articles)}] Evaluating: {title}")

        try:
            result = evaluate_article(article, llm, prompt_template=template)
            article.relevance_score = result["relevance_score"]
            article.evaluation = result
            print(f"  → Score: {result['relevance_score']}/10 | {result.get('action_needed', 'n/a')}")
            print(f"  → {result.get('reasoning', '')[:120]}")
        except Exception as e:
            logger.warning(f"Evaluation failed for '{title}': {e}")
            article.relevance_score = None
            article.evaluation = {"error": str(e)}
            print(f"  ⚠️  Evaluation failed: {e}")

    return articles
