"""Remote monitoring agent — runs on a monitored host.

Exposes the same REST API endpoints so that a remote client (or the
TUI / web dashboard) can connect and pull metrics.

Usage::

    raven serve --host 0.0.0.0 --port 9090
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException

from raven.config import RavenConfig, load_config
from raven.core.collector import Collector


def create_remote_app(config: RavenConfig | None = None) -> FastAPI:
    """Create the remote agent FastAPI application."""
    cfg = config or load_config()
    collector = Collector(cfg)
    api_key = cfg.remote.api_key

    app = FastAPI(
        title="Raven Remote Agent",
        version="0.1.0",
        description="Remote system monitoring agent",
    )

    # ── API key middleware ───────────────────────────────────────────
    if api_key:
        @app.middleware("http")
        async def _check_api_key(request: Request, call_next):
            key = request.headers.get("X-API-Key", "")
            if key != api_key:
                raise HTTPException(status_code=401, detail="Invalid API key")
            return await call_next(request)

    # ── REST: full snapshot ──────────────────────────────────────────
    @app.get("/api/v1/snapshot")
    async def snapshot():
        snap = await collector.collect_async()
        return asdict(snap)

    # ── REST: individual modules ─────────────────────────────────────
    @app.get("/api/v1/{module}")
    async def module_data(module: str):
        snap = await collector.collect_async()
        data = asdict(snap)
        result = data.get(module)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Unknown module: {module}")
        return {"module": module, "timestamp": data["timestamp"], "data": result}

    # ── WebSocket ────────────────────────────────────────────────────
    @app.websocket("/ws/live")
    async def ws_live(websocket: WebSocket):
        if api_key:
            key = websocket.query_params.get("api_key", "")
            if key != api_key:
                await websocket.close(code=4001, reason="Invalid API key")
                return

        await websocket.accept()
        try:
            while True:
                snap = await collector.collect_async()
                await websocket.send_text(json.dumps(asdict(snap), default=str))
                await asyncio.sleep(cfg.general.refresh_interval)
        except WebSocketDisconnect:
            pass
        except Exception:
            try:
                await websocket.close()
            except Exception:
                pass

    # ── Health check ─────────────────────────────────────────────────
    @app.get("/health")
    async def health():
        return {"status": "ok", "agent": "raven"}

    return app
