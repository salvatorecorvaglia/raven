"""FastAPI web dashboard and REST API server.

Endpoints:
    GET  /                     Web dashboard
    GET  /api/v1/snapshot      Full JSON snapshot
    GET  /api/v1/{module}      Individual module data
    WS   /ws/live              WebSocket live streaming
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from raven.config import RavenConfig, load_config
from raven.core.collector import Collector

_STATIC_DIR = Path(__file__).parent / "static"

# Module names valid for the individual endpoints
_VALID_MODULES = {
    "cpu", "memory", "disk", "network", "processes",
    "users", "sensors", "containers", "system_info",
}


def create_app(config: RavenConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    cfg = config or load_config()
    collector = Collector(cfg)
    api_key = cfg.web.api_key

    app = FastAPI(
        title="Raven System Monitor",
        version="0.1.0",
        description="Cross-platform system monitoring REST API",
    )

    # ── API key middleware ───────────────────────────────────────────
    if api_key:
        @app.middleware("http")
        async def _check_api_key(request: Request, call_next):
            # Skip auth for static files and the root page
            path = request.url.path
            if path == "/" or path.startswith("/static"):
                return await call_next(request)
            key = request.headers.get("X-API-Key", "")
            if key != api_key:
                raise HTTPException(status_code=401, detail="Invalid API key")
            return await call_next(request)

    # ── Static files ─────────────────────────────────────────────────
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    # ── HTML dashboard ───────────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        index = _STATIC_DIR / "index.html"
        return index.read_text(encoding="utf-8")

    # ── REST: full snapshot ──────────────────────────────────────────
    @app.get("/api/v1/snapshot")
    async def snapshot():
        snap = await collector.collect_async()
        return asdict(snap)

    # ── REST: individual modules ─────────────────────────────────────
    @app.get("/api/v1/{module}")
    async def module_data(module: str):
        if module not in _VALID_MODULES:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown module '{module}'. Valid: {sorted(_VALID_MODULES)}",
            )
        snap = await collector.collect_async()
        data = asdict(snap)
        result = data.get(module)
        if result is None:
            raise HTTPException(status_code=404, detail=f"No data for module '{module}'")
        return {"module": module, "timestamp": data["timestamp"], "data": result}

    # ── WebSocket: live stream ───────────────────────────────────────
    @app.websocket("/ws/live")
    async def ws_live(websocket: WebSocket):
        # API key check for WebSocket
        if api_key:
            key = websocket.query_params.get("api_key", "")
            if key != api_key:
                await websocket.close(code=4001, reason="Invalid API key")
                return

        await websocket.accept()
        try:
            while True:
                snap = await collector.collect_async()
                payload = json.dumps(asdict(snap), default=str)
                await websocket.send_text(payload)
                await asyncio.sleep(cfg.general.refresh_interval)
        except WebSocketDisconnect:
            pass
        except Exception:
            try:
                await websocket.close()
            except Exception:
                pass

    return app
