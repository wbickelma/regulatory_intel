from __future__ import annotations
"""RSS.app API client for generating RSS feeds from website URLs."""

import logging
from dataclasses import dataclass
from typing import Optional
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


class RssAppClient:
    """Client for RSS.app API.
    
    API Docs: https://rss.app/docs/api
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
