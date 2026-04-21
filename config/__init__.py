"""
Config Package
==============

Centralized configuration management for the regulatory news summarizer.

Contains application settings, logging configuration, and GCP-specific
configuration. All settings are loaded from environment variables to
support local development and cloud deployment without code changes.

Modules:
    - settings: App-wide settings (database URLs, API keys, feature flags)
    - logging_config: Structured JSON logging setup for Cloud Logging
    - gcp: GCP project, bucket, and service configuration
"""
