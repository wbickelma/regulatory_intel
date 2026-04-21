"""
Investigator Agent
==================

Responsible for the onboarding investigation of new websites.
Probes a submitted URL to determine the optimal ingestion strategy.

Tools:
    - GPT Researcher: Autonomous web research agent that navigates the
      target site and discovers available data sources.
    - Pydantic: Structures the agent's findings into validated models.

Strategy Waterfall:
    1. RSS / Atom Feed  → Most stable, richest metadata
    2. Sitemap XML       → Good coverage, limited metadata
    3. ScrapeGraphAI     → Fallback when no structured feeds exist

Modules:
    - agent.py: Core investigation logic and GPT Researcher orchestration
    - prompts.py: Prompt templates for site investigation
    - strategy_selector.py: Waterfall decision logic

Input:
    - A validated site URL (from the onboarding step)

Output:
    - SiteInvestigationResult (schemas.investigation)
    - StrategyDecision (schemas.investigation)
"""
