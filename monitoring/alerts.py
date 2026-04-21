"""
Alert Engine
============

Detects anomalies in pipeline execution and routes alerts to operators.

Alert Triggers:
    - Pipeline Failure: run.py threw an unhandled exception.
    - Zero Yield: A run completed but fetched 0 articles across all sites
      (suggests a structural failure, IP ban, or API key expiry).
    - Degraded Site: A specific site has failed extraction for 3
      consecutive days.

Routing:
    - In MVP, alerts are written as CRITICAL level logs.
    - In production, GCP Log-based Alerts can trap these CRITICAL logs
      and route them to email or Slack.
"""
