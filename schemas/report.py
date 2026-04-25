"""
Report Schemas
==============

Pydantic models for generated reports.
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ReportGenerate(BaseModel):
    """Schema for triggering report generation."""
    topic_id: UUID | None = Field(None, description="Specific topic or None for all")
    days: int = Field(7, ge=1, le=30, description="Days to look back")


class ReportResponse(BaseModel):
    """Schema for report API responses."""
    id: UUID
    topic_id: UUID | None
    date_range_start: datetime
    date_range_end: datetime
    summary_markdown: str
    article_count: int
    generated_at: datetime
    
    class Config:
        from_attributes = True


class ReportList(BaseModel):
    """Schema for list of reports."""
    reports: list[ReportResponse]
    total: int


class ReportSummary(BaseModel):
    """Brief report metadata without full content."""
    id: UUID
    topic_id: UUID | None
    date_range_start: datetime
    date_range_end: datetime
    article_count: int
    generated_at: datetime
    
    class Config:
        from_attributes = True
