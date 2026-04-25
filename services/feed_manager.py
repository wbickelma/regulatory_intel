"""Feed management service for topics and RSS subscriptions."""

from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.orm import Session

from clients import RssAppClient, InoreaderClient
from db.models import Topic, FeedConfig


class FeedManager:
    """Manages topics and feed subscriptions.
    
    Coordinates between RSS.app (feed generation) and Inoreader (aggregation).
    """
    
    def __init__(
        self,
        db: Session,
        rss_client: RssAppClient,
        inoreader_client: InoreaderClient
    ):
        self.db = db
        self.rss_client = rss_client
        self.inoreader_client = inoreader_client
    
    async def create_topic(self, name: str, description: str = "") -> Topic:
        """Create a new topic with corresponding Inoreader folder.
        
        Args:
            name: Topic name (e.g., "FDA Regulations").
            description: Optional description.
            
        Returns:
            Created Topic object.
        """
        folder = await self.inoreader_client.create_folder(name)
        
        topic = Topic(
            id=uuid4(),
            name=name,
            description=description,
            inoreader_folder_id=folder.folder_id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        self.db.add(topic)
        self.db.commit()
        self.db.refresh(topic)
        return topic
    
    async def add_feed(
        self,
        topic_id: UUID,
        source_url: str,
        name: str
    ) -> FeedConfig:
        """Add a feed to a topic.
        
        Creates RSS feed via RSS.app and subscribes in Inoreader.
        
        Args:
            topic_id: The topic to add the feed to.
            source_url: Original website URL.
            name: Display name for the feed.
            
        Returns:
            Created FeedConfig object.
        """
        topic = self.db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise ValueError(f"Topic {topic_id} not found")
        
        feed_response = await self.rss_client.get_or_create_feed(source_url)
        
        subscription = await self.inoreader_client.subscribe_to_feed(
            feed_url=feed_response.feed_url,
            folder_id=topic.inoreader_folder_id,
            title=name
        )
        
        feed_config = FeedConfig(
            id=uuid4(),
            topic_id=topic_id,
            source_url=source_url,
            feed_url=feed_response.feed_url,
            inoreader_subscription_id=subscription.subscription_id,
            name=name,
            is_active=True,
            created_at=datetime.utcnow()
        )
        self.db.add(feed_config)
        self.db.commit()
        self.db.refresh(feed_config)
        return feed_config
    
    def list_topics(self, active_only: bool = True) -> list[Topic]:
        """List all topics.
        
        Args:
            active_only: If True, only return active topics.
            
        Returns:
            List of Topic objects.
        """
        query = self.db.query(Topic)
        if active_only:
            query = query.filter(Topic.is_active == True)
        return query.all()
    
    def list_feeds(self, topic_id: UUID, active_only: bool = True) -> list[FeedConfig]:
        """List feeds for a topic.
        
        Args:
            topic_id: The topic ID.
            active_only: If True, only return active feeds.
            
        Returns:
            List of FeedConfig objects.
        """
        query = self.db.query(FeedConfig).filter(FeedConfig.topic_id == topic_id)
        if active_only:
            query = query.filter(FeedConfig.is_active == True)
        return query.all()
    
    def get_topic(self, topic_id: UUID) -> Topic | None:
        """Get a topic by ID."""
        return self.db.query(Topic).filter(Topic.id == topic_id).first()
    
    async def deactivate_topic(self, topic_id: UUID) -> bool:
        """Deactivate a topic and all its feeds.
        
        Args:
            topic_id: The topic ID.
            
        Returns:
            True if successful.
        """
        topic = self.get_topic(topic_id)
        if not topic:
            return False
        
        topic.is_active = False
        self.db.query(FeedConfig).filter(
            FeedConfig.topic_id == topic_id
        ).update({"is_active": False})
        self.db.commit()
        return True
    
    async def deactivate_feed(self, feed_id: UUID) -> bool:
        """Deactivate a feed.
        
        Args:
            feed_id: The feed ID.
            
        Returns:
            True if successful.
        """
        feed = self.db.query(FeedConfig).filter(FeedConfig.id == feed_id).first()
        if not feed:
            return False
        
        await self.inoreader_client.unsubscribe(feed.inoreader_subscription_id)
        
        feed.is_active = False
        self.db.commit()
        return True
