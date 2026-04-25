"""Scheduled job entrypoints.

- weekly_report: Generates and delivers the weekly regulatory briefing
"""

from .weekly_report import run_weekly_report

__all__ = ["run_weekly_report"]
