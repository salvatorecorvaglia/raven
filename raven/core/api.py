"""Shared API factory for web and remote servers.

Eliminates code duplication between ``web/server.py`` and
``remote/server.py`` by providing a common FastAPI app builder
with API key middleware, snapshot endpoints, and WebSocket streaming.
"""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
import sys
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from raven.config import RavenConfig
from raven.core.collector import Collector

log = logging.getLogger(__name__)

# Module names valid for individual endpoints
VALID_MODULES = frozenset(
    {
        "cpu",
        "memory",
        "disk",
        "network",
        "processes",
        "users",
        "sensors",
        "containers",
        "system_info",
    }
)


def _warn_open_bind(host: str, api_key: str, service_name: str) -> None:
    """Log a security warning if binding to all interfaces with no auth."""
    if host == "0.0.0.0" and not api_key:
        log.warning(
            "⚠️  %s is binding to 0.0.0.0 with no API key. "
            "System metrics will be exposed to the entire network. "
            "Set an api_key or bind to 127.0.0.1.",
            service_name,
        )
        print(
            f"⚠️  WARNING: {service_name} is binding to 0.0.0.0 with no API key. "
            "System metrics are exposed to the network.",
            file=sys.stderr,
        )


def create_base_app(
    *,
    config: RavenConfig,
    collector: Collector,
    title: str,
    description: str,
    api_key: str = "",
    skip_auth_paths: frozenset[str] | None = None,
) -> FastAPI:
    """Create a FastAPI app with shared monitoring endpoints.

    Parameters
    ----------
    config:
        Raven configuration.
    collector:
        The metric collector instance.
    title:
        FastAPI app title.
    description:
        FastAPI app description.
    api_key:
        API key for authentication (empty = no auth).
    skip_auth_paths:
        URL path prefixes to skip auth for (e.g. static files).
    """
    from raven import __version__

    app = FastAPI(
        title=title,
        version=__version__,
        description=description,
    )

    # ── CORS ─────────────────────────────────────────────────────────
    # The web dashboard is served from the same origin so no CORS is
    # needed.  Keep the middleware for explicit opt-in later, but
    # default to NO allowed origins to prevent cross-origin data leaks.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["X-API-Key"],
    )

    # ── API key middleware (timing-safe) ─────────────────────────────
    _skip = skip_auth_paths or frozenset()

    if api_key:

        @app.middleware("http")
        async def _check_api_key(request: Request, call_next):
            path = request.url.path
            if any(path.startswith(prefix) for prefix in _skip):
                return await call_next(request)
            key = request.headers.get("X-API-Key", "")
            if not hmac.compare_digest(key, api_key):
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
        if module not in VALID_MODULES:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown module '{module}'. Valid: {sorted(VALID_MODULES)}",
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
        await websocket.accept()
        try:
            # Authenticate via first message if an API key is configured.
            # This avoids leaking the key in URL query params (logs, history).
            if api_key:
                try:
                    auth_msg = await asyncio.wait_for(websocket.receive_text(), timeout=10)
                except asyncio.TimeoutError:
                    await websocket.close(code=4001, reason="Auth timeout")
                    return
                if not hmac.compare_digest(auth_msg, api_key):
                    await websocket.close(code=4001, reason="Invalid API key")
                    return

            while True:
                snap = await collector.collect_async()
                payload = json.dumps(asdict(snap), default=str)
                await websocket.send_text(payload)
                await asyncio.sleep(config.general.refresh_interval)
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
        return {"status": "ok", "agent": "raven", "version": __version__}

    return app
