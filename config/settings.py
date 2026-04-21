"""
Application Settings
====================

Loads and validates all application-wide configuration from environment
variables using Pydantic BaseSettings.

Responsibilities:
    - Database connection strings (Cloud SQL)
    - LLM provider API keys and model selections
    - GCS bucket names and paths
    - Feature flags and operational thresholds
    - Rate limiting defaults
    - Scheduler cadence settings

Usage:
    from config.settings import settings
    print(settings.database_url)
    print(settings.circuit_base_url)

Environment Variables:
    DATABASE_URL          - PostgreSQL connection string
    CIRCUIT_CLIENT_ID     - Circuit API OAuth2 client ID
    CIRCUIT_CLIENT_SECRET - Circuit API OAuth2 client secret
    CIRCUIT_APPKEY        - Circuit API application key
    CIRCUIT_TOKEN_URL     - Circuit IdP token endpoint (default: Cisco IdP)
    CIRCUIT_BASE_URL      - Circuit chat base URL (default: chat-ai.cisco.com)
    CIRCUIT_API_VERSION   - Circuit Azure API version
    CIRCUIT_MODEL         - Default chat model served by Circuit
    GCS_BUCKET_RAW        - GCS bucket for raw extracted articles
    GCS_BUCKET_APPROVED   - GCS bucket/path for evaluated articles
    GCS_BUCKET_SUMMARIES  - GCS bucket/path for final summaries
    LOG_LEVEL             - Logging level (DEBUG, INFO, WARNING, ERROR)

Notes:
    - All secrets should be stored in GCP Secret Manager in production.
    - A .env file is supported for local development via .env.example.
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central settings loaded from env vars / .env file."""

    # --- Database ---
    database_url: str = "sqlite:///local_mode.db"

    # --- Circuit API (firm's enterprise LLM gateway) ---
    # Endpoints / version default to the values used in the firm's
    # reference implementation (``circuit_scrapegraph_example.py``).
    circuit_client_id: str = ""
    circuit_client_secret: str = ""
    circuit_appkey: str = ""
    circuit_token_url: str = "https://id.cisco.com/oauth2/default/v1/token"
    circuit_base_url: str = "https://chat-ai.cisco.com/"
    circuit_api_version: str = "2025-04-01-preview"
    circuit_model: str = "gpt-5-nano"

    # --- Retriever: Google Programmable Search (Custom Search) ---
    google_custom_search_api: str = ""
    google_cx: str = ""

    # --- Embeddings: local sentence-transformers model path ---
    # Absolute path to a sentence-transformers model folder used by
    # GPT Researcher for context compression.  When empty, the model ID
    # is passed to HuggingFace, which requires network access.
    local_embedding_model_path: str = ""

    # --- GCS ---
    gcs_bucket_raw: str = ""
    gcs_bucket_approved: str = ""
    gcs_bucket_summaries: str = ""

    # --- Operational ---
    log_level: str = "INFO"
    investigation_timeout_seconds: int = 120
    max_rss_staleness_days: int = 90
    max_sitemap_staleness_days: int = 180

    model_config = {
        "env_file": str(Path(__file__).resolve().parents[1] / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
