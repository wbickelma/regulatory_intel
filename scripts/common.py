"""Shared setup for scripts.

Loads credentials from .env and initializes API clients.
"""
from __future__ import annotations

import os
import sys

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from clients.rss_app import RssAppClient
from clients.inoreader import InoreaderClient, InoreaderAuthManager

# Paths
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# Default parameters
SOURCE_URL = "https://www.fedramp.gov/blog/1/"
TARGET_FOLDER = "test_folder2"
DAYS_BACK = 1


def load_credentials() -> dict:
    """Load and validate API credentials from .env."""
    creds = {
        "app_id": os.getenv("CLIENT_ID_INOREADER"),
        "app_key": os.getenv("CLIENT_SECRET_INOREADER"),
        "access_token": os.getenv("INOREADER_ACCESS_TOKEN"),
        "refresh_token": os.getenv("INOREADER_REFRESH_TOKEN"),
        "rss_key": os.getenv("RSS_APP_KEY"),
        "rss_secret": os.getenv("RSS_APP_SECRET"),
    }

    required = {k: v for k, v in creds.items() if k != "refresh_token"}
    if not all(required.values()):
        print("\n❌ Missing credentials in .env file!")
        for name, val in required.items():
            print(f"  {name:30s} {'✅' if val else '❌ MISSING'}")
        sys.exit(1)

    print("✅ All credentials loaded from .env")
    return creds


def get_inoreader_client(creds: dict) -> InoreaderClient:
    """Build an InoreaderClient from credentials dict."""
    auth_manager = InoreaderAuthManager(
        app_id=creds["app_id"],
        app_key=creds["app_key"],
        access_token=creds["access_token"],
        refresh_token=creds["refresh_token"],
    )
    return InoreaderClient(
        app_id=creds["app_id"],
        app_key=creds["app_key"],
        auth_manager=auth_manager,
    )


def get_rss_client(creds: dict) -> RssAppClient:
    """Build an RssAppClient from credentials dict."""
    return RssAppClient(api_key=creds["rss_key"], api_secret=creds["rss_secret"])
