"""
Pipeline Run Orchestrator
=========================

Orchestrates a full scheduled pipeline run across all active sites
(or a specific site).

This is the main entry point triggered by Cloud Scheduler on a
recurring cadence.

Steps:
    1. Generate a unique run_id for tracing
    2. Load all active sites and their configurations from the database
    3. For each site:
        a. Gather new links (pipeline/gather.py)
        b. Extract content from new links (pipeline/extract.py)
        c. Evaluate extracted articles (pipeline/evaluate.py)
    4. Collect all approved articles across all sites
    5. Generate the synthesized briefing (pipeline/summarize.py)
    6. Store the briefing and deliver to configured channels
    7. Log run summary (sites processed, articles found, articles approved)

Input:
    - Optional: site_id (int) to run for a single site
    - Optional: date_from / date_to filters

Output:
    - BriefingSummary stored in GCS and database
    - Run log with full metrics

Dependencies:
    - pipeline.gather
    - pipeline.extract
    - pipeline.evaluate
    - pipeline.summarize
    - db, storage, config

Error Handling:
    - If one site fails, log the error and continue with remaining sites.
      A single site failure should never halt the entire run.
    - If all sites fail, generate an error alert and a "No results" briefing.
    - All errors are logged with run_id and site_id for traceability.
"""
