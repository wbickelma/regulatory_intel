"""Article extraction service for pulling content from Inoreader."""

from uuid import UUID, uuid4
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from clients import InoreaderClient
from db.models import Topic, FeedConfig, Article


class ArticleExtractor:
    """Extracts articles from Inoreader within date ranges.
    
    Handles deduplication and full content retrieval.
    """
    
    def __init__(self, db: Session, inoreader_client: InoreaderClient):
        self.db = db
        self.inoreader_client = inoreader_client
    
    async def extract_articles(
        self,
        topic_id: UUID,
        days: int = 7
    ) -> list[Article]:
        """Extract articles for a topic within date range.
        
        Args:
            topic_id: The topic ID.
            days: Number of days to look back.
            
        Returns:
            List of Article objects (new and existing).
        """
        topic = self.db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise ValueError(f"Topic {topic_id} not found")
        
        since = datetime.utcnow() - timedelta(days=days)
        
        items = await self.inoreader_client.get_folder_items(
            folder_id=topic.inoreader_folder_id,
            since=since
        )
        
        articles = []
        for item in items:
            existing = self.db.query(Article).filter(
                Article.inoreader_item_id == item.item_id
            ).first()
            
            if existing:
                articles.append(existing)
                continue
            
            content = await self.inoreader_client.get_article_content(item.item_id)
            
            feed = self.db.query(FeedConfig).filter(
                FeedConfig.topic_id == topic_id,
                FeedConfig.is_active == True
            ).first()
            
            article = Article(
                id=uuid4(),
                feed_id=feed.id if feed else None,
                inoreader_item_id=item.item_id,
                title=content.title,
                source_url=content.url,
                published_at=content.published_at,
                content_markdown=content.content_text,
                is_relevant=None,
                relevance_reasoning=None,
                extracted_at=datetime.utcnow()
            )
            self.db.add(article)
            articles.append(article)
        
        self.db.commit()
        return articles
    
    async def extract_all_articles(self, days: int = 7) -> dict[UUID, list[Article]]:
        """Extract articles for all active topics.
        
        Args:
            days: Number of days to look back.
            
        Returns:
            Dict mapping topic_id to list of articles.
        """
        topics = self.db.query(Topic).filter(Topic.is_active == True).all()
        
        result = {}
        for topic in topics:
            result[topic.id] = await self.extract_articles(topic.id, days)
        
        return result
    
    def get_unclassified_articles(self, topic_id: UUID) -> list[Article]:
        """Get articles that haven't been classified yet.
        
        Args:
            topic_id: The topic ID.
            
        Returns:
            List of unclassified Article objects.
        """
        feeds = self.db.query(FeedConfig.id).filter(
            FeedConfig.topic_id == topic_id
        ).subquery()
        
        return self.db.query(Article).filter(
            Article.feed_id.in_(feeds),
            Article.is_relevant == None
        ).all()
    
    def get_relevant_articles(
        self,
        topic_id: UUID,
        days: int = 7
    ) -> list[Article]:
        """Get relevant articles for a topic within date range.
        
        Args:
            topic_id: The topic ID.
            days: Number of days to look back.
            
        Returns:
            List of relevant Article objects.
        """
        since = datetime.utcnow() - timedelta(days=days)
        
        feeds = self.db.query(FeedConfig.id).filter(
            FeedConfig.topic_id == topic_id
        ).subquery()
        
        return self.db.query(Article).filter(
            Article.feed_id.in_(feeds),
            Article.is_relevant == True,
            Article.published_at >= since
        ).all()
