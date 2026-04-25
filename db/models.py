"""
ORM Models
==========

SQLAlchemy ORM model definitions for the RSS-based pipeline.

Tables:
    Topic
        - id, name, description, inoreader_folder_id, is_active, created_at
        - Represents a regulatory topic mapped to an Inoreader folder.

    FeedConfig
        - id, topic_id (FK), source_url, feed_url, inoreader_subscription_id,
          name, is_active, created_at
        - RSS feed configuration. source_url is the original website,
          feed_url is the RSS.app generated feed.

    Article
        - id, feed_id (FK), inoreader_item_id, title, source_url,
          published_at, content_markdown, is_relevant, relevance_reasoning,
          extracted_at
        - Article extracted from Inoreader with LLM classification.

    Report
        - id, topic_id (FK, nullable), date_range_start, date_range_end,
          summary_markdown, article_count, generated_at
        - Generated executive briefing.

Dependencies:
    - SQLAlchemy
    - db.session (Base declarative class)
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.session import Base


class Topic(Base):
    """Regulatory topic mapped to an Inoreader folder."""
    
    __tablename__ = "topics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, default="")
    inoreader_folder_id = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    feeds = relationship("FeedConfig", back_populates="topic")
    reports = relationship("Report", back_populates="topic")


class FeedConfig(Base):
    """RSS feed subscription configuration."""
    
    __tablename__ = "feed_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id"), nullable=False)
    source_url = Column(String(2000), nullable=False)
    feed_url = Column(String(2000), nullable=False)
    inoreader_subscription_id = Column(String(500), nullable=False)
    name = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    topic = relationship("Topic", back_populates="feeds")
    articles = relationship("Article", back_populates="feed")


class Article(Base):
    """Extracted article with classification status."""
    
    __tablename__ = "articles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    feed_id = Column(UUID(as_uuid=True), ForeignKey("feed_configs.id"), nullable=True)
    inoreader_item_id = Column(String(500), unique=True, nullable=False)
    title = Column(String(1000), nullable=False)
    source_url = Column(String(2000), nullable=False)
    published_at = Column(DateTime, nullable=False)
    content_markdown = Column(Text)
    is_relevant = Column(Boolean, nullable=True)
    relevance_reasoning = Column(Text, nullable=True)
    extracted_at = Column(DateTime, default=datetime.utcnow)
    
    feed = relationship("FeedConfig", back_populates="articles")


class Report(Base):
    """Generated regulatory briefing."""
    
    __tablename__ = "reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id"), nullable=True)
    date_range_start = Column(DateTime, nullable=False)
    date_range_end = Column(DateTime, nullable=False)
    summary_markdown = Column(Text, nullable=False)
    article_count = Column(Integer, default=0)
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    topic = relationship("Topic", back_populates="reports")
