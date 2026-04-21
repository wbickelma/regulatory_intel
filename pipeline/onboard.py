"""
Onboarding Pipeline
===================

Orchestrates the full onboarding flow for a new website.

Steps:
    1. Validate the submitted URL (reachability, domain extraction,
       duplicate detection)
    2. Store the initial site record in the database
    3. Invoke the investigator agent to probe the site
    4. Run the strategy selector waterfall on investigation results
    5. Store the strategy configuration in site_configs table
    6. Log the onboarding result

Input:
    - SiteCreate (schemas.site) — URL and metadata from the user

Output:
    - SiteRecord with associated SiteConfig stored in the database
    - StrategyDecision logged for audit trail

Dependencies:
    - agents.investigator (GPT Researcher + strategy selector)
    - db (sites + site_configs tables)
    - config.logging_config

Error Handling:
    - If URL validation fails → return error to user, do not proceed
    - If investigation fails → store site with status="investigation_failed",
      log the error, alert monitoring
    - If strategy confidence is low → store config but log a warning
"""
