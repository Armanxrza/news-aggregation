"""Passenger/LiteSpeed WSGI entry — wraps the FastAPI app (no duplicate routers)."""

from __future__ import annotations

import os
import sys
import traceback

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

os.environ.setdefault("ADMIN_AUTH_DISABLED", "false")
os.environ.setdefault("ENABLE_CRAWL_SCHEDULER", "false")

try:
    from a2wsgi import ASGIMiddleware
    from main import app as fastapi_app

    application = ASGIMiddleware(fastapi_app)
except Exception:  # noqa: BLE001
    _ERR = traceback.format_exc()

    def application(environ, start_response):
        start_response(
            "500 Internal Server Error",
            [("Content-Type", "application/json; charset=utf-8")],
        )
        payload = (
            '{"error":"SajhaNews failed to initialize","detail":'
            + repr(_ERR)
            + "}"
        )
        return [payload.encode("utf-8")]
