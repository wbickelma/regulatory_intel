"""
Article Schemas
===============

Pydantic models for articles extracted from Inoreader.

Models:
    ArticleBase - Core article attributes from Inoreader stream
    ArticleCreate - Internal schema for creating article records
    ArticleResponse - API response schema with classification status
    ArticleList - Paginated list response
    ArticleClassification - Classification result from LLM
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ArticleBase(BaseModel):
    """Base article attributes from Inoreader."""
    title: str
    source_url: str
    published_at: datetime


class ArticleCreate(ArticleBase):
    """Schema for creating an article record."""
    inoreader_item_id: str
    content_markdown: str


class ArticleResponse(ArticleBase):
    """Schema for article API responses."""
    id: UUID
    feed_id: UUID | None
    inoreader_item_id: str
    content_markdown: str
    is_relevant: bool | None
    relevance_reasoning: str | None
    extracted_at: datetime
    
    class Config:
        from_attributes = True


class ArticleList(BaseModel):
    """Schema for list of articles."""
    articles: list[ArticleResponse]
    total: int
    topic_id: UUID | None = None
    days: int = 7


class ArticleClassification(BaseModel):
    """Schema for article classification result."""
    article_id: UUID
    is_relevant: bool
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)
