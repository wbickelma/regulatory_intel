"""
Logging Configuration
=====================

Sets up structured JSON logging compatible with Google Cloud Logging.

Responsibilities:
    - Configure Python logging with structured JSON formatters
    - Attach run_id, site_id, and stage_name to log records for traceability
    - Route logs to stdout for Cloud Run/Cloud Logging ingestion
    - Provide a consistent logger factory for all modules

Usage:
    from config.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("Pipeline started", extra={"run_id": "abc123", "site_id": 42})

Output Format:
    {
        "timestamp": "2026-04-15T10:30:00Z",
        "severity": "INFO",
        "module": "pipeline.run",
        "message": "Pipeline started",
        "run_id": "abc123",
        "site_id": 42
    }
"""

import json
import logging
import sys
from datetime import datetime, timezone


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON for Cloud Logging ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        # Propagate optional tracing fields when present.
        for field in ("run_id", "site_id", "stage_name", "url"):
            value = getattr(record, field, None)
            if value is not None:
                log_entry[field] = value

        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a module-level logger with structured JSON output on stdout."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
    return logger
