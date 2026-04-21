"""
Site Schemas
============

Pydantic models for website registration and configuration.

Models:
    SiteCreate
        - Input model for onboarding a new site.
        - Fields: url, jurisdiction, expected_update_frequency, notes

    SiteRecord
        - Full site record as stored in the database.
        - Fields: id, url, domain, jurisdiction, status, created_by,
                  created_at, expected_update_frequency

    SiteConfig
        - Strategy configuration for a site.
        - Fields: site_id, strategy (RSS/SITEMAP/SCRAPEGRAPHAI),
                  feed_url, sitemap_url, target_paths, confidence_score,
                  version

    StrategyEnum
        - Enum: RSS, SITEMAP, SCRAPEGRAPHAI

Usage:
    from schemas.site import SiteCreate, SiteConfig, StrategyEnum

    new_site = SiteCreate(url="https://sec.gov/news", jurisdiction="US")
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, HttpUrl, field_validator


class StrategyEnum(str, Enum):
    """Supported ingestion strategies, ordered by reliability."""

    RSS = "RSS"
    SITEMAP = "SITEMAP"
    SCRAPEGRAPHAI = "SCRAPEGRAPHAI"


class SiteCreate(BaseModel):
    """Input schema for registering a new website for monitoring."""

    url: HttpUrl
    jurisdiction: str = "US"
    expected_update_frequency: str = "daily"
    notes: str = ""


class SiteRecord(BaseModel):
    """Database-backed representation of a monitored site."""

    id: int
    url: str
    domain: str
    jurisdiction: str
    status: str = "pending"
    created_by: str = "system"
    created_at: datetime = datetime.utcnow()
    expected_update_frequency: str = "daily"


class SiteConfig(BaseModel):
    """
    Strategy configuration produced by the investigator and consumed
    by the daily pipeline.
    """

    site_id: int
    strategy: StrategyEnum
    feed_url: Optional[str] = None
    sitemap_url: Optional[str] = None
    target_paths: list[str] = []
    confidence_score: float = 0.0
    version: int = 1

    @field_validator("confidence_score")
    @classmethod
    def _clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))
