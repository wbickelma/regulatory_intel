#!/usr/bin/env python3
"""
Pipeline Scheduler
==================

HTTP server for triggering the daily pipeline.
Can be invoked by Cloud Scheduler or run as a standalone service.

Endpoints:
    GET  /           - Health check
    POST /run        - Trigger pipeline run
    GET  /status     - Get last run status

Usage:
    # Run as HTTP server (for Cloud Scheduler)
    python jobs/scheduler.py --port 8080
    
    # Run pipeline directly (for cron)
    python jobs/scheduler.py --run-now

Environment Variables:
    PORT - Server port (default: 8080)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from config.settings import settings
from config.logging_config import setup_logging
from jobs.daily_pipeline import run_pipeline

logger = logging.getLogger(__name__)

# Global state for last run
last_run_status: Optional[dict] = None
is_running: bool = False


class SchedulerHandler(BaseHTTPRequestHandler):
    """HTTP handler for scheduler endpoints."""
    
    def _send_json(self, data: dict, status: int = 200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/" or self.path == "/health":
            self._send_json({
                "status": "healthy",
                "service": "regulatory-intelligence-pipeline",
                "timestamp": datetime.utcnow().isoformat(),
            })
        elif self.path == "/status":
            self._send_json({
                "is_running": is_running,
                "last_run": last_run_status,
            })
        else:
            self._send_json({"error": "Not found"}, 404)
    
    def do_POST(self):
        """Handle POST requests."""
        global is_running, last_run_status
        
        if self.path == "/run":
            if is_running:
                self._send_json({
                    "status": "already_running",
                    "message": "Pipeline is already running",
                }, 409)
                return
            
            # Parse request body for options
            content_length = int(self.headers.get("Content-Length", 0))
            body = {}
            if content_length > 0:
                body = json.loads(self.rfile.read(content_length))
            
            # Start pipeline in background thread
            def run_in_background():
                global is_running, last_run_status
                is_running = True
                try:
                    summary = run_pipeline(
                        days_back=body.get("days_back"),
                        relevance_threshold=body.get("threshold"),
                        topics=body.get("topics"),
                        dry_run=body.get("dry_run", False),
                    )
                    last_run_status = {
                        "status": "success",
                        "completed_at": datetime.utcnow().isoformat(),
                        "summary": summary,
                    }
                except Exception as e:
                    logger.error(f"Pipeline failed: {e}")
                    last_run_status = {
                        "status": "failed",
                        "completed_at": datetime.utcnow().isoformat(),
                        "error": str(e),
                    }
                finally:
                    is_running = False
            
            thread = Thread(target=run_in_background)
            thread.start()
            
            self._send_json({
                "status": "started",
                "message": "Pipeline started in background",
                "started_at": datetime.utcnow().isoformat(),
            }, 202)
        else:
            self._send_json({"error": "Not found"}, 404)
    
    def log_message(self, format, *args):
        """Override to use Python logging."""
        logger.info("%s - %s", self.address_string(), format % args)


def run_server(port: int = 8080):
    """Start the HTTP server."""
    server = HTTPServer(("0.0.0.0", port), SchedulerHandler)
    logger.info(f"🚀 Scheduler server running on port {port}")
    logger.info(f"   Health: http://localhost:{port}/")
    logger.info(f"   Trigger: POST http://localhost:{port}/run")
    logger.info(f"   Status: http://localhost:{port}/status")
    server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="Pipeline scheduler")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 8080)))
    parser.add_argument("--run-now", action="store_true", help="Run pipeline immediately and exit")
    parser.add_argument("--dry-run", action="store_true", help="Skip GCS upload")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    log_level = "DEBUG" if args.debug else settings.log_level
    setup_logging(log_level)
    
    if args.run_now:
        # Run pipeline directly
        logger.info("Running pipeline directly...")
        summary = run_pipeline(dry_run=args.dry_run)
        print(json.dumps(summary, indent=2))
    else:
        # Start HTTP server
        run_server(args.port)


if __name__ == "__main__":
    main()
