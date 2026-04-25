"""Pydantic schemas for FeedConfig model."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl


class FeedBase(BaseModel):
    """Base feed attributes."""
    name: str = Field(..., min_length=1, max_length=200)
    source_url: str = Field(..., description="Original website URL")


class FeedCreate(FeedBase):
    """Schema for creating a feed."""
    pass


class FeedUpdate(BaseModel):
    """Schema for updating a feed."""
    name: str | None = None
    is_active: bool | None = None


class FeedResponse(FeedBase):
    """Schema for feed API responses."""
    id: UUID
    topic_id: UUID
    feed_url: str
    inoreader_subscription_id: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class FeedList(BaseModel):
    """Schema for list of feeds."""
    feeds: list[FeedResponse]
    total: int


class FeedHealth(BaseModel):
    """Schema for feed health check response."""
    feed_id: UUID
    name: str
    is_active: bool
    last_fetch: datetime | None
    item_count: int
    status: str = Field(..., description="healthy, stale, or error")
