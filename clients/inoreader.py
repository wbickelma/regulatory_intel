from __future__ import annotations
"""Inoreader API client for feed aggregation and article extraction.

Supports OAuth2 authentication with token refresh.
Provides both sync and async methods for flexibility.
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import httpx
import requests

logger = logging.getLogger(__name__)


@dataclass
class FolderResponse:
    folder_id: str
    name: str


@dataclass
class SubscriptionResponse:
    subscription_id: str
    feed_url: str
    folder_id: str
    title: str


@dataclass
class ArticleItem:
    item_id: str
    title: str
    url: str
    published_at: datetime
    source: Optional[str] = None
    summary: Optional[str] = None
    full_content: Optional[str] = None
    ai_summary: Optional[str] = None
    relevance_score: Optional[int] = None
    evaluation: Optional[dict] = field(default=None, repr=False)

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict."""
        d = asdict(self)
        d["published_at"] = self.published_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ArticleItem":
        """Deserialize from a dict."""
        data = dict(d)
        pub = data.get("published_at")
        if isinstance(pub, str):
            data["published_at"] = datetime.fromisoformat(pub)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ArticleContent:
    item_id: str
    title: str
    url: str
    published_at: datetime
    content_html: str
    content_text: str


class InoreaderAuthManager:
    """Manages OAuth2 tokens with automatic refresh."""
    
    TOKEN_FILE = "inoreader_tokens.json"
    AUTH_URL = "https://www.inoreader.com/oauth2/auth"
    TOKEN_URL = "https://www.inoreader.com/oauth2/token"
    
    def __init__(
        self,
        app_id: str,
        app_key: str,
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_path: str | None = None,
    ):
        self.app_id = app_id
        self.app_key = app_key
        self.token_path = Path(token_path or self.TOKEN_FILE)
        self._access_token: str | None = access_token
        self._refresh_token: str | None = refresh_token
        self._expires_at: datetime | None = None
    
    def load_tokens(self) -> bool:
        """Load tokens from file, but only if no tokens were provided at init."""
        # If tokens were provided via constructor (e.g. from .env), keep them
        if self._access_token:
            return True
        
        if not self.token_path.exists():
            return False
        
        try:
            data = json.loads(self.token_path.read_text())
            self._access_token = data.get("access_token")
            self._refresh_token = data.get("refresh_token")
            expires = data.get("expires_at")
            self._expires_at = datetime.fromisoformat(expires) if expires else None
            return bool(self._access_token)
        except Exception as e:
            logger.warning(f"Failed to load tokens: {e}")
            return False
    
    def save_tokens(self) -> None:
        """Save tokens to file."""
        data = {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "expires_at": self._expires_at.isoformat() if self._expires_at else None
        }
        self.token_path.write_text(json.dumps(data, indent=2))
    
    def is_expired(self) -> bool:
        """Check if access token is expired."""
        if not self._expires_at:
            return True
        return datetime.utcnow() >= self._expires_at
    
    async def refresh_access_token(self) -> str:
        """Refresh the access token using refresh token."""
        if not self._refresh_token:
            raise ValueError("No refresh token available")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.app_id,
                    "client_secret": self.app_key,
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token
                }
            )
            response.raise_for_status()
            data = response.json()
        
        self._access_token = data["access_token"]
        self._refresh_token = data.get("refresh_token", self._refresh_token)
        expires_in = data.get("expires_in", 3600)
        self._expires_at = datetime.utcnow().replace(
            second=datetime.utcnow().second + expires_in
        )
        self.save_tokens()
        logger.info("Inoreader access token refreshed")
        return self._access_token
    
    async def get_access_token(self) -> str:
        """Get valid access token, refreshing if needed (async)."""
        self.load_tokens()
        
        if self._access_token and not self.is_expired():
            return self._access_token
        
        if self._refresh_token:
            return await self.refresh_access_token()
        
        raise ValueError("No valid tokens. Run OAuth flow first.")
    
    def get_access_token_sync(self) -> str:
        """Get valid access token, refreshing if needed (sync)."""
        self.load_tokens()
        
        if self._access_token and not self.is_expired():
            return self._access_token
        
        if self._refresh_token:
            return self.refresh_access_token_sync()
        
        raise ValueError("No valid tokens. Run OAuth flow first.")
    
    def refresh_access_token_sync(self) -> str:
        """Refresh the access token using refresh token (sync)."""
        if not self._refresh_token:
            raise ValueError("No refresh token available")
        
        logger.info("🔄 Refreshing access token...")
        response = requests.post(
            self.TOKEN_URL,
            data={
                "client_id": self.app_id,
                "client_secret": self.app_key,
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token
            }
        )
        response.raise_for_status()
        data = response.json()
        
        self._access_token = data["access_token"]
        self._refresh_token = data.get("refresh_token", self._refresh_token)
        expires_in = data.get("expires_in", 3600)
        self._expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        self.save_tokens()
        logger.info("✅ Access token refreshed")
        return self._access_token
    
    def exchange_auth_code(self, auth_code: str, redirect_uri: str = "http://localhost") -> dict:
        """Exchange authorization code for initial tokens (one-time setup)."""
        logger.info("Exchanging auth code for tokens...")
        response = requests.post(
            self.TOKEN_URL,
            data={
                "code": auth_code,
                "client_id": self.app_id,
                "client_secret": self.app_key,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }
        )
        if response.status_code == 200:
            tokens = response.json()
            self._access_token = tokens["access_token"]
            self._refresh_token = tokens.get("refresh_token")
            expires_in = tokens.get("expires_in", 3600)
            self._expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            self.save_tokens()
            logger.info("✅ Initial tokens saved")
            return tokens
        else:
            raise ValueError(f"Failed to exchange auth code: {response.text}")
    
    def get_auth_url(self, redirect_uri: str = "http://localhost", state: str = "774411") -> str:
        """Generate the OAuth authorization URL for user consent."""
        return (
            f"{self.AUTH_URL}/?client_id={self.app_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code&scope=read%20write&state={state}"
        )


class InoreaderClient:
    """Client for Inoreader API (Professional/Enterprise tier).
    
    Supports OAuth2 authentication with automatic token refresh.
    API Docs: https://www.inoreader.com/developers
    """
    
    BASE_URL = "https://www.inoreader.com/reader/api/0"
    
    def __init__(
        self,
        app_id: str,
        app_key: str,
        auth_manager: InoreaderAuthManager | None = None
    ):
        self.app_id = app_id
        self.app_key = app_key
        self.auth_manager = auth_manager or InoreaderAuthManager(app_id, app_key)
        self._client: httpx.AsyncClient | None = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client with valid auth headers."""
        access_token = await self.auth_manager.get_access_token()
        
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "AppId": self.app_id
                }
            )
        else:
            self._client.headers["Authorization"] = f"Bearer {access_token}"
        
        return self._client
    
    async def create_folder(self, name: str) -> FolderResponse:
        """Create a new folder (tag) for organizing feeds.
        
        Args:
            name: Folder name (maps to a topic).
            
        Returns:
            FolderResponse with the created folder ID.
        """
        client = await self._get_client()
        tag_name = f"user/-/label/{name}"
        response = await client.post(
            "/edit-tag",
            params={"a": tag_name}
        )
        response.raise_for_status()
        return FolderResponse(folder_id=tag_name, name=name)
    
    async def subscribe_to_feed(
        self, 
        feed_url: str, 
        folder_id: str,
        title: Optional[str] = None
    ) -> SubscriptionResponse:
        """Subscribe to an RSS feed and add it to a folder.
        
        Args:
            feed_url: The RSS feed URL.
            folder_id: The folder/tag ID to add the subscription to.
            title: Optional custom title for the subscription.
            
        Returns:
            SubscriptionResponse with subscription details.
        """
        client = await self._get_client()
        
        # Step 1: quickadd to subscribe
        response = await client.post(
            "/subscription/quickadd",
            params={"quickadd": feed_url}
        )
        response.raise_for_status()
        data = response.json()
        stream_id = data.get("streamId", "")
        
        # Step 2: edit to tag with folder
        await client.post(
            "/subscription/edit",
            params={"ac": "edit", "s": stream_id, "a": folder_id, "t": title or ""}
        )
        
        return SubscriptionResponse(
            subscription_id=data.get("streamId", ""),
            feed_url=feed_url,
            folder_id=folder_id,
            title=title or data.get("streamName", "")
        )
    
    async def get_folder_items(
        self,
        folder_id: str,
        since: datetime,
        until: Optional[datetime] = None,
        count: int = 1000
    ) -> list[ArticleItem]:
        """Fetch article items from a folder within a date range.
        
        Args:
            folder_id: The folder/tag ID.
            since: Start of date range.
            until: End of date range (defaults to now).
            count: Maximum number of items to return.
            
        Returns:
            List of ArticleItem objects.
        """
        client = await self._get_client()
        params = {
            "n": count,
            "ot": int(since.timestamp())
        }
        if until:
            params["nt"] = int(until.timestamp())
            
        response = await client.get(
            f"/stream/contents/{folder_id}",
            params=params
        )
        response.raise_for_status()
        data = response.json()
        
        items = []
        for item in data.get("items", []):
            items.append(ArticleItem(
                item_id=item["id"],
                title=item.get("title", ""),
                url=item.get("canonical", [{}])[0].get("href", ""),
                published_at=datetime.fromtimestamp(item.get("published", 0)),
                source=item.get("origin", {}).get("title"),
                summary=item.get("summary", {}).get("content")
            ))
        return items
    
    async def get_article_content(self, item_id: str) -> ArticleContent:
        """Get full article content for an item.
        
        Args:
            item_id: The Inoreader item ID.
            
        Returns:
            ArticleContent with full text.
        """
        client = await self._get_client()
        response = await client.get(
            "/stream/contents",
            params={"i": item_id}
        )
        response.raise_for_status()
        data = response.json()
        
        item = data.get("items", [{}])[0]
        content = item.get("content", {}) or item.get("summary", {})
        
        return ArticleContent(
            item_id=item_id,
            title=item.get("title", ""),
            url=item.get("canonical", [{}])[0].get("href", ""),
            published_at=datetime.fromtimestamp(item.get("published", 0)),
            content_html=content.get("content", ""),
            content_text=self._strip_html(content.get("content", ""))
        )
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a feed.
        
        Args:
            subscription_id: The subscription/stream ID.
            
        Returns:
            True if successful.
        """
        client = await self._get_client()
        response = await client.post(
            "/subscription/edit",
            params={"ac": "unsubscribe", "s": subscription_id}
        )
        return response.status_code == 200
    
    @staticmethod
    def _strip_html(html: str) -> str:
        """Basic HTML tag stripping."""
        import re
        clean = re.sub(r'<[^>]+>', '', html)
        return ' '.join(clean.split())
    
    # ========== SYNC METHODS FOR TESTING ==========
    
    def add_feed_to_folder_sync(
        self,
        feed_url: str,
        folder_name: str
    ) -> SubscriptionResponse | None:
        """Subscribe to a feed and add to folder (sync version).
        
        Args:
            feed_url: The RSS feed URL.
            folder_name: Name of the folder/label.
            
        Returns:
            SubscriptionResponse or None on failure.
        """
        access_token = self.auth_manager.get_access_token_sync()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Step 1: Subscribe via quickadd
        print(f"\n--- Subscribing to {feed_url} ---")
        add_response = requests.post(
            f"{self.BASE_URL}/subscription/quickadd",
            headers=headers,
            data={
                "quickadd": feed_url,
                "AppId": self.app_id,
                "AppKey": self.app_key
            }
        )
        
        if add_response.status_code != 200:
            print(f"❌ Failed to subscribe: {add_response.text}")
            return None
        
        try:
            feed_id = add_response.json().get("streamId")
            print(f"✅ Subscribed! Feed ID: {feed_id}")
        except Exception as e:
            print(f"❌ Could not parse response: {e}")
            return None
        
        # Step 2: Tag with folder
        print(f"\n--- Moving feed to folder: '{folder_name}' ---")
        folder_tag = f"user/-/label/{folder_name}"
        
        edit_response = requests.post(
            f"{self.BASE_URL}/subscription/edit",
            headers=headers,
            data={
                "ac": "edit",
                "s": feed_id,
                "a": folder_tag,
                "AppId": self.app_id,
                "AppKey": self.app_key
            }
        )
        
        if edit_response.status_code == 200:
            print(f"🚀 Successfully added feed to '{folder_name}'!")
            return SubscriptionResponse(
                subscription_id=feed_id,
                feed_url=feed_url,
                folder_id=folder_tag,
                title=""
            )
        else:
            print(f"❌ Failed to move to folder: {edit_response.text}")
            return None
    
    def get_folder_articles_sync(
        self,
        folder_name: str,
        days_back: int = 7,
        max_items: int = 50
    ) -> list[ArticleItem]:
        """Fetch articles from a folder within timeframe (sync version).
        
        Args:
            folder_name: Name of the folder/label.
            days_back: Number of days to look back.
            max_items: Maximum items to fetch.
            
        Returns:
            List of ArticleItem objects.
        """
        print(f"\n--- Fetching articles from '{folder_name}' (Last {days_back} days) ---")
        
        access_token = self.auth_manager.get_access_token_sync()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        stream_id = f"user/-/label/{folder_name}"
        cutoff_time = int(time.time()) - (days_back * 24 * 60 * 60)
        
        response = requests.get(
            f"{self.BASE_URL}/stream/contents/{stream_id}",
            headers=headers,
            params={
                "AppId": self.app_id,
                "AppKey": self.app_key,
                "n": max_items,
                "ot": cutoff_time
            }
        )
        
        if response.status_code != 200:
            print(f"❌ Error fetching folder contents: {response.text}")
            return []
        
        data = response.json()
        items = data.get("items", [])
        print(f"✅ Found {len(items)} articles.\n")
        
        articles = []
        for item in items:
            title = item.get("title", "No Title")
            published_ts = item.get("published", 0)
            pub_date = datetime.fromtimestamp(published_ts)
            link = item.get("canonical", [{}])[0].get("href", "")
            
            articles.append(ArticleItem(
                item_id=item["id"],
                title=title,
                url=link,
                published_at=pub_date,
                source=item.get("origin", {}).get("title"),
                summary=item.get("summary", {}).get("content")
            ))
            
            print(f"📰 {title}")
            print(f"🕒 {pub_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🔗 {link}\n")
        
        return articles
    
    def get_article_content_sync(self, item_id: str) -> Optional[str]:
        """Fetch full article content via the Mobilizer API (sync).
        
        Uses GET /reader/api/0/mobilize to load the full content
        for a given article.
        
        Args:
            item_id: The Inoreader item ID (long or short format).
            
        Returns:
            Full article content HTML string, or None on failure.
        """
        access_token = self.auth_manager.get_access_token_sync()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        short_id = self._to_short_id(item_id)
        
        response = requests.get(
            f"{self.BASE_URL}/mobilize",
            headers=headers,
            params={
                "AppId": self.app_id,
                "AppKey": self.app_key,
                "i": short_id,
            }
        )
        
        if response.status_code == 503:
            logger.warning(f"Mobilizer returned 503 for item {short_id}")
            return None
        
        if response.status_code != 200:
            logger.warning(f"Mobilizer error {response.status_code}: {response.text}")
            return None
        
        # Response body may be plain text "Error" or empty even on 200
        try:
            data = response.json()
        except (requests.exceptions.JSONDecodeError, ValueError):
            body_preview = response.text[:200] if response.text else "(empty)"
            logger.warning(f"Mobilizer returned non-JSON for item {short_id}: {body_preview}")
            return None
        
        return data.get("content")
    
    @staticmethod
    def _to_short_id(item_id: str) -> str:
        """Convert a long-form Inoreader item ID to short format.
        
        Long format:  'tag:google.com,2005:reader/item/00000000148b9369'
        Short format: '344691561'  (hex → signed base-10 decimal)
        
        If already a decimal string, returns as-is.
        """
        if "/" in item_id:
            hex_str = item_id.rsplit("/", 1)[-1]
        else:
            hex_str = item_id
        
        # Convert 16-char unsigned hex to signed 64-bit decimal
        value = int(hex_str, 16)
        if value >= (1 << 63):
            value -= (1 << 64)
        return str(value)
    
    async def close(self):
        if self._client:
            await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()
