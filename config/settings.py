"""
Application Settings
====================

Loads configuration from environment variables using Pydantic BaseSettings.

Usage:
    from config.settings import settings
    print(settings.gcs_bucket_name)

Environment Variables:
    GCS_BUCKET_NAME - GCS bucket for storing results
    LOG_LEVEL       - Logging level (DEBUG, INFO, WARNING, ERROR)

Note: Most API credentials are loaded via os.getenv() directly in each client.
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central settings loaded from env vars / .env file."""

    # --- GCP / Cloud Storage ---
    gcs_bucket_name: str = "regulatory-intelligence-results"

    # --- Operational ---
    log_level: str = "INFO"

    model_config = {
        "env_file": str(Path(__file__).resolve().parents[1] / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
