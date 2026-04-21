"""
Scheduler Package
=================

Defines the recurring jobs that drive the automated pipeline.

When deployed to GCP, Cloud Scheduler triggers an HTTP endpoint
(e.g., POST /runs), so a dedicated Python scheduler isn't strictly
necessary. However, this package serves as documentation for the
cron schedules and can run locally using APScheduler.

Modules:
    - jobs.py: Cron schedule definitions and APScheduler setup
      for local development.
"""
