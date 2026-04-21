"""
Investigation Schemas
=====================

Pydantic models for the output of the site investigation agent
(GPT Researcher) and the strategy selection waterfall.

Models:
    RSSFeedInfo
        - A discovered RSS/Atom feed.
        - Fields: url, description, is_active, last_entry_date

    SitemapInfo
        - A discovered sitemap.
        - Fields: url, type (standard/index), estimated_entry_count

    SiteInvestigationResult
        - Full structured output from the investigation agent.
        - Fields: rss_feeds (list[RSSFeedInfo]), sitemaps (list[SitemapInfo]),
                  content_paths (list[str]), recommended_strategy (StrategyEnum),
                  confidence (float 0.0-1.0), notes (str)

    StrategyDecision
        - Final output of the strategy selection waterfall.
        - Fields: strategy, target_url, confidence, reasoning

Usage:
    from schemas.investigation import SiteInvestigationResult

    result = SiteInvestigationResult(**agent_output)
    print(result.recommended_strategy)

Notes:
    - The investigation agent is prompted to return JSON matching these models.
    - Validation ensures at least one strategy is always recommended.
    - confidence < 0.5 should trigger a warning in logs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from schemas.site import StrategyEnum


class RSSFeedInfo(BaseModel):
    """A discovered RSS or Atom feed on the target site."""

    url: str
    description: str = ""
    is_active: bool = False
    last_entry_date: Optional[datetime] = None


class SitemapInfo(BaseModel):
    """A discovered sitemap on the target site."""

    url: str
    type: str = "standard"  # "standard" or "index"
    estimated_entry_count: int = 0


class SiteInvestigationResult(BaseModel):
    """
    Structured output from the investigation agent consolidating
    all discovered ingestion options for a target website.
    """

    rss_feeds: list[RSSFeedInfo] = []
    sitemaps: list[SitemapInfo] = []
    content_paths: list[str] = []
    recommended_strategy: StrategyEnum = StrategyEnum.SCRAPEGRAPHAI
    confidence: float = 0.0
    notes: str = ""

    @field_validator("confidence")
    @classmethod
    def _clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class StrategyDecision(BaseModel):
    """
    Final output of the strategy-selection waterfall.
    Contains the chosen strategy, the URL to use, a confidence
    score, and human-readable reasoning.
    """

    strategy: StrategyEnum
    target_url: str
    confidence: float
    reasoning: str

    @field_validator("confidence")
    @classmethod
    def _clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))
