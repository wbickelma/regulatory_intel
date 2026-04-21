"""
Scheduler Jobs
==============

Defines the recurring pipeline schedules.

Schedules:
    Full Pipeline Run
        - Description: Gathers, extracts, evaluates, and summarizes
          updates for all active sites.
        - GCP Cron: 0 17 * * 1-5 (5 PM Mon-Fri)

    Retry Failed Extractions
        - Description: Attempts to recrawl links that failed extraction
          due to temporary network issues.
        - GCP Cron: 0 12 * * * (Daily at Noon)

Notes:
    - Local development can use APScheduler to mimic Cloud Scheduler.
    - Ensure jobs do not overlap destructively.
"""
