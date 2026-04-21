"""
Pipeline Package
================

Orchestration modules that chain together agents, gatherers,
extractors, and storage into end-to-end workflows.

Pipeline modules are the glue layer. They know the order of
operations but delegate all real work to the specialized modules.

Modules:
    - onboard.py: Full onboarding flow (validate → investigate → save config)
    - run.py: Full scheduled pipeline run (gather → extract → evaluate → summarize)
    - gather.py: Orchestrates the correct gatherer based on site config
    - extract.py: Orchestrates Crawl4AI extraction for a batch of links
    - evaluate.py: Orchestrates LLM evaluation for a batch of articles
    - summarize.py: Orchestrates map-reduce summarization

Flow:
    Onboarding (one-time per site):
        onboard.py → agents/investigator → db (site_configs)

    Scheduled Run (recurring):
        run.py → gather.py → extract.py → evaluate.py → summarize.py
"""
