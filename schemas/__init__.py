"""
Schemas Package
===============

Pydantic models for API requests/responses and internal data contracts.

Modules:
    - topic: Topic (folder) management schemas
    - feed: RSS feed configuration schemas  
    - article: Article extraction and classification schemas
    - report: Report generation schemas

Design Principles:
    - All API endpoints use these Pydantic models for validation.
    - Models map to SQLAlchemy ORM models in db/models.py.
    - Separate Create/Update/Response schemas per resource.
"""

from .topic import TopicCreate, TopicUpdate, TopicResponse, TopicList
from .feed import FeedCreate, FeedUpdate, FeedResponse, FeedList
from .article import ArticleResponse, ArticleList, ArticleClassification
from .report import ReportResponse, ReportList, ReportGenerate

__all__ = [
    "TopicCreate", "TopicUpdate", "TopicResponse", "TopicList",
    "FeedCreate", "FeedUpdate", "FeedResponse", "FeedList",
    "ArticleResponse", "ArticleList", "ArticleClassification",
    "ReportResponse", "ReportList", "ReportGenerate",
]
