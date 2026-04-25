"""RSS.app API client for generating RSS feeds from website URLs.

Implements feed discovery before creation to avoid duplicates.
Provides both sync and async methods for flexibility.
"""

import logging
from dataclasses import dataclass
from typing import Optional
import httpx
import requests

logger = logging.getLogger(__name__)


@dataclass
class FeedResponse:
    feed_id: str
    feed_url: str
    source_url: str
    status: str
    title: str = ""
    is_existing: bool = False


@dataclass
class FeedStatus:
    feed_id: str
    is_active: bool
    last_fetch: Optional[str]
    item_count: int


class RssAppClient:
    """Client for RSS.app API.
    
    Implements the feed discovery workflow:
    1. Search for existing feed matches
    2. Create new feed only if no match found
    
    API Docs: https://rss.app/docs/api
    
    Note: Authentication uses Bearer token with format "key:secret"
    """
    
    BASE_URL = "https://api.rss.app/v1"
    
    def __init__(self, api_key: str, api_secret: str | None = None):
        """Initialize RSS.app client.
        
        Args:
            api_key: RSS.app API key (or combined key:secret string)
            api_secret: RSS.app API secret (optional if key contains both)
        """
        if api_secret:
            self.auth_token = f"{api_key}:{api_secret}"
        else:
            self.auth_token = api_key
            
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
        )
    
    async def search_existing_feed(self, url: str) -> FeedResponse | None:
        """Search for an existing feed for this URL.
        
        Args:
            url: The source website URL.
            
        Returns:
            FeedResponse if found, None otherwise.
        """
        try:
            response = await self._client.get(
                "/feeds",
                params={"url": url}
            )
            response.raise_for_status()
            data = response.json()
            
            feeds = data.get("feeds", [])
            if feeds:
                feed = feeds[0]
                logger.info(f"Found existing feed for {url}")
                return FeedResponse(
                    feed_id=feed["id"],
                    feed_url=feed["feed_url"],
                    source_url=url,
                    status=feed.get("status", "active"),
                    is_existing=True
                )
        except httpx.HTTPStatusError:
            pass
        
        return None
    
    async def get_or_create_feed(self, url: str) -> FeedResponse:
        """Get existing feed or create new one for a URL.
        
        This is the primary method to use. It implements the workflow:
        1. Search for existing feed matches
        2. Create new feed only if no match found
        
        Args:
            url: The source website URL.
            
        Returns:
            FeedResponse (existing or newly created).
        """
        existing = await self.search_existing_feed(url)
        if existing:
            return existing
        
        logger.info(f"Creating new feed for {url}")
        return await self._create_feed(url)
    
    async def _create_feed(self, url: str) -> FeedResponse:
        """Create a new RSS feed (internal, use get_or_create_feed).
        
        Args:
            url: The source website URL to create a feed from.
            
        Returns:
            FeedResponse with the generated feed URL.
        """
        response = await self._client.post(
            "/feeds",
            json={"url": url}
        )
        response.raise_for_status()
        data = response.json()
        return FeedResponse(
            feed_id=data["id"],
            feed_url=data["feed_url"],
            source_url=url,
            status=data.get("status", "active"),
            is_existing=False
        )
    
    async def get_feed_status(self, feed_id: str) -> FeedStatus:
        """Check the health status of a feed.
        
        Args:
            feed_id: The RSS.app feed ID.
            
        Returns:
            FeedStatus with current feed health info.
        """
        response = await self._client.get(f"/feeds/{feed_id}")
        response.raise_for_status()
        data = response.json()
        return FeedStatus(
            feed_id=feed_id,
            is_active=data.get("is_active", True),
            last_fetch=data.get("last_fetch"),
            item_count=data.get("item_count", 0)
        )
    
    async def delete_feed(self, feed_id: str) -> bool:
        """Delete a feed.
        
        Args:
            feed_id: The RSS.app feed ID.
            
        Returns:
            True if deletion was successful.
        """
        response = await self._client.delete(f"/feeds/{feed_id}")
        return response.status_code == 204
    
    # ========== SYNC METHODS FOR TESTING ==========
    
    def create_feed_sync(self, source_url: str) -> FeedResponse | None:
        """Generate an RSS feed from a URL (sync version).
        
        Args:
            source_url: The website URL to create a feed from.
            
        Returns:
            FeedResponse with the generated feed URL, or None on failure.
        """
        print(f"\n--- Generating RSS feed for: {source_url} ---")
        
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{self.BASE_URL}/feeds",
            headers=headers,
            json={"url": source_url}
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            title = data.get("title", "Unknown Title")
            feed_url = data.get("rss_feed_url")
            
            print(f"✅ Feed successfully generated!")
            print(f"Title: {title}")
            print(f"RSS Feed URL: {feed_url}")
            
            return FeedResponse(
                feed_id=data.get("id", ""),
                feed_url=feed_url,
                source_url=source_url,
                status="active",
                title=title,
                is_existing=False
            )
        elif response.status_code == 401:
            print("❌ 401 Unauthorized. Check your API Key and Secret.")
        elif response.status_code == 403:
            print("❌ 403 Forbidden. RSS.app API typically requires a Pro Plan.")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
        
        return None
    
    async def close(self):
        await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()
