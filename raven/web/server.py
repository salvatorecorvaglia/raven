"""FastAPI web dashboard and REST API server.

Endpoints:
    GET  /                     Web dashboard
    GET  /api/v1/snapshot      Full JSON snapshot
    GET  /api/v1/{module}      Individual module data
    WS   /ws/live              WebSocket live streaming
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from raven.config import RavenConfig, load_config
from raven.core.api import create_base_app, warn_open_bind
from raven.core.collector import Collector

_STATIC_DIR = Path(__file__).parent / "static"


def create_app(config: RavenConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI web dashboard application."""
    cfg = config or load_config()
    collector = Collector(cfg)
    api_key = cfg.web.api_key

    warn_open_bind(cfg.web.host, api_key, "Web dashboard")

    app = create_base_app(
        config=cfg,
        collector=collector,
        title="Raven System Monitor",
        description="Cross-platform system monitoring REST API",
        api_key=api_key,
        skip_auth_paths=frozenset({"/", "/static"}),
    )

    # ── Static files ─────────────────────────────────────────────────
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    # Pre-load HTML dashboard template in memory on startup
    index_html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")

    # ── HTML dashboard ───────────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return index_html

    return app
