"""Pydantic schemas for Topic model."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class TopicBase(BaseModel):
    """Base topic attributes."""
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="")


class TopicCreate(TopicBase):
    """Schema for creating a topic."""
    pass


class TopicUpdate(BaseModel):
    """Schema for updating a topic."""
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class TopicResponse(TopicBase):
    """Schema for topic API responses."""
    id: UUID
    inoreader_folder_id: str
    is_active: bool
    created_at: datetime
    feed_count: int = 0
    
    class Config:
        from_attributes = True


class TopicList(BaseModel):
    """Schema for list of topics."""
    topics: list[TopicResponse]
    total: int
