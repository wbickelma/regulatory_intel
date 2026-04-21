"""
GCP Configuration
=================

Google Cloud Platform-specific configuration and client initialization.

Responsibilities:
    - GCP project ID and region settings
    - Cloud Storage client initialization
    - Cloud SQL connection helpers
    - Cloud Scheduler references
    - Service account and IAM configuration references

Usage:
    from config.gcp import get_storage_client, GCP_PROJECT_ID
    client = get_storage_client()

Notes:
    - In local development, uses Application Default Credentials (ADC).
    - In production (Cloud Run), uses the attached service account automatically.
    - Ensure required GCP APIs are enabled: Cloud Storage, Cloud SQL, Cloud Scheduler.
"""
