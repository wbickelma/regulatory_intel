"""
Application Settings
====================

Loads and validates all application-wide configuration from environment
variables using Pydantic BaseSettings.

Usage:
    from config.settings import settings
    print(settings.circuit_base_url)

Environment Variables:
    CIRCUIT_CLIENT_ID     - Circuit API OAuth2 client ID
    CIRCUIT_CLIENT_SECRET - Circuit API OAuth2 client secret
    CIRCUIT_APPKEY        - Circuit API application key
    CIRCUIT_BASE_URL      - Circuit chat base URL (default: chat-ai.cisco.com)
    CIRCUIT_API_VERSION   - Circuit Azure API version
    CIRCUIT_MODEL         - Default chat model served by Circuit
    CLIENT_ID_INOREADER   - Inoreader OAuth2 application ID
    CLIENT_SECRET_INOREADER - Inoreader OAuth2 application secret
    RSS_APP_KEY           - RSS.app API key
    RSS_APP_SECRET        - RSS.app API secret
    GCP_PROJECT_ID        - Google Cloud project ID
    GCS_BUCKET_NAME       - GCS bucket for storing results
    LOG_LEVEL             - Logging level (DEBUG, INFO, WARNING, ERROR)

Notes:
    - A .env file is supported for local development.
"""

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central settings loaded from env vars / .env file."""

    # --- Circuit API (firm's enterprise LLM gateway) ---
    circuit_client_id: str = ""
    circuit_client_secret: str = ""
    circuit_appkey: str = ""
    circuit_token_url: str = "https://id.cisco.com/oauth2/default/v1/token"
    circuit_base_url: str = "https://chat-ai.cisco.com/"
    circuit_api_version: str = "2025-04-01-preview"
    circuit_model: str = "gpt-5-nano"

    # --- Inoreader API ---
    client_id_inoreader: str = ""
    client_secret_inoreader: str = ""
    inoreader_access_token: str = ""
    inoreader_refresh_token: str = ""

    # --- RSS.app API ---
    rss_app_key: str = ""
    rss_app_secret: str = ""

    # --- Gemini API ---
    gemini_api_key: str = ""

    # --- GCP / Cloud Storage ---
    # GCS credentials loaded via os.getenv() directly in gcs_client.py
    # to avoid pydantic parsing issues with multiline private keys.
    # Required env vars: GCP_PROJECT_ID, GCS_CLIENT_EMAIL, GCS_PRIVATE_KEY
    gcs_bucket_name: str = "regulatory-intelligence-results"

    # --- Pipeline Settings ---
    relevance_threshold: int = 6
    days_back: int = 1

    # --- Operational ---
    log_level: str = "INFO"

    model_config = {
        "env_file": str(Path(__file__).resolve().parents[1] / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Topic folders to process (Inoreader folder names)
TOPIC_FOLDERS: List[str] = [
    "Antitrust",
    "Trade and Export",
    "Labor & Workforce",
    "Hardware Manufacturing",
    "Financial Reporting & Tax",
    "AI Telecom",
    "AI Governance",
    "Supply Chain",
    "test_folder1",
    "Environmental Sustainability",
    "Data Protecton and Privacy",
    "Competition/Antitrust",
    "AI / Data / Networking & Security Technologies",
    "AI & Emerging Technology Governance",
    "Telecom",
    "Cybersecurity"
]

settings = Settings()
