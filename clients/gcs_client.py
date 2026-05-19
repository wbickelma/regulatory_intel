"""
Google Cloud Storage Client
============================

Handles uploading pipeline results to GCS bucket.

Usage:
    from clients.gcs_client import GCSClient
    
    client = GCSClient()
    client.upload_topic_results("AI_Governance", articles)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from google.cloud import storage
from google.oauth2 import service_account

from config.settings import settings

if TYPE_CHECKING:
    from clients.inoreader import ArticleItem

logger = logging.getLogger(__name__)


class GCSClient:
    """Client for uploading results to Google Cloud Storage."""

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        credentials_path: Optional[str] = None,
    ):
        self.bucket_name = bucket_name or settings.gcs_bucket_name
        
        # Initialize client with credentials
        import os
        credentials = self._build_credentials(credentials_path)
        project_id = os.getenv("GCP_PROJECT_ID")
        if credentials:
            self._client = storage.Client(credentials=credentials, project=project_id)
        else:
            # Use default credentials (workload identity, ADC, etc.)
            self._client = storage.Client()
        
        self._bucket = self._client.bucket(self.bucket_name)
        logger.info(f"GCS client initialized for bucket: {self.bucket_name}")

    def _build_credentials(self, credentials_path: Optional[str] = None):
        """Build credentials from env vars directly."""
        import os
        
        # Read directly from env (bypass pydantic parsing issues with multiline keys)
        client_email = os.getenv("GCS_CLIENT_EMAIL")
        private_key = os.getenv("GCS_PRIVATE_KEY")
        project_id = os.getenv("GCP_PROJECT_ID")
        private_key_id = os.getenv("GCS_PRIVATE_KEY_ID", "")
        
        if client_email and private_key:
            private_key = private_key.replace("\\n", "\n")
            creds_info = {
                "type": "service_account",
                "project_id": project_id,
                "private_key_id": private_key_id,
                "private_key": private_key,
                "client_email": client_email,
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            return service_account.Credentials.from_service_account_info(creds_info)
        
        return None

    def upload_topic_results(
        self,
        topic: str,
        articles: List["ArticleItem"],
        date: Optional[datetime] = None,
    ) -> str:
        """Upload evaluated articles for a topic to GCS.
        
        Args:
            topic: Topic/folder name
            articles: List of ArticleItem objects with content
            date: Date for the results (defaults to today)
            
        Returns:
            GCS blob path where results were uploaded
        """
        if date is None:
            date = datetime.utcnow()
        
        # Create blob path: results/{topic_name}_{dd_mm_yyyy}.json
        date_str = date.strftime("%d_%m_%Y")
        blob_path = f"results/{topic}_{date_str}.json"
        
        # Serialize articles to JSON
        data = {
            "topic": topic,
            "date": date_str,
            "generated_at": datetime.utcnow().isoformat(),
            "article_count": len(articles),
            "articles": [a.to_dict() for a in articles],
        }
        
        # Upload to GCS
        blob = self._bucket.blob(blob_path)
        blob.upload_from_string(
            json.dumps(data, indent=2, ensure_ascii=False),
            content_type="application/json",
        )
        
        logger.info(f"✅ Uploaded {len(articles)} articles to gs://{self.bucket_name}/{blob_path}")
        return f"gs://{self.bucket_name}/{blob_path}"

    def upload_daily_summary(
        self,
        summary: dict,
        date: Optional[datetime] = None,
    ) -> str:
        """Upload daily pipeline summary to GCS.
        
        Args:
            summary: Dict with pipeline run statistics
            date: Date for the summary (defaults to today)
            
        Returns:
            GCS blob path where summary was uploaded
        """
        if date is None:
            date = datetime.utcnow()
        
        date_str = date.strftime("%Y-%m-%d")
        blob_path = f"summaries/{date_str}.json"
        
        summary["date"] = date_str
        summary["generated_at"] = datetime.utcnow().isoformat()
        
        blob = self._bucket.blob(blob_path)
        blob.upload_from_string(
            json.dumps(summary, indent=2, ensure_ascii=False),
            content_type="application/json",
        )
        
        logger.info(f"✅ Uploaded daily summary to gs://{self.bucket_name}/{blob_path}")
        return f"gs://{self.bucket_name}/{blob_path}"

    def list_topic_results(self, topic: str, limit: int = 30) -> List[str]:
        """List recent result files for a topic.
        
        Args:
            topic: Topic/folder name
            limit: Max number of results to return
            
        Returns:
            List of blob paths
        """
        prefix = f"results/{topic}/"
        blobs = self._bucket.list_blobs(prefix=prefix)
        paths = sorted([b.name for b in blobs], reverse=True)[:limit]
        return paths

    def download_result(self, blob_path: str) -> dict:
        """Download and parse a result JSON file.
        
        Args:
            blob_path: Path to blob (without gs://bucket/)
            
        Returns:
            Parsed JSON data
        """
        blob = self._bucket.blob(blob_path)
        content = blob.download_as_string()
        return json.loads(content)
