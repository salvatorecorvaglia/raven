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
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from raven.config import RavenConfig
from raven.core.collector import Collector
from raven.core.utils import serialize_model as asdict

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

# Upper bound on concurrent WebSocket clients per server.  The broadcast loop
# sends to every client serially, so an unbounded set lets one viewer degrade
# the stream for all of them.
MAX_WEBSOCKET_CLIENTS = 64

# Per-client send timeout, so a stalled socket cannot block the broadcast loop.
_WS_SEND_TIMEOUT = 5.0


def warn_open_bind(host: str, api_key: str, service_name: str) -> None:
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


def keys_match(candidate: str, expected: str) -> bool:
    """Constant-time API key comparison that tolerates non-ASCII keys.

    ``hmac.compare_digest`` raises ``TypeError`` when given ``str`` arguments
    containing non-ASCII characters, so both sides are encoded to UTF-8 first.
    """
    return hmac.compare_digest(candidate.encode("utf-8"), expected.encode("utf-8"))


def create_base_app(
    *,
    config: RavenConfig,
    collector: Collector,
    title: str,
    description: str,
    api_key: str = "",
    skip_auth_paths: frozenset[str] | None = None,
    owns_collector: bool = True,
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
        Exact URL paths, or path prefixes whose children (``prefix + "/"``)
        are also exempt, to skip auth for (e.g. static files).
    owns_collector:
        Whether this app is responsible for the collector's lifecycle.  Must
        be ``False`` when the collector is shared with another consumer (e.g.
        the TUI running a background web server), otherwise app shutdown
        would tear down a collector still in use.
    """
    from raven import __version__

    active_websockets: set[WebSocket] = set()

    def _active_modules() -> frozenset[str]:
        """Modules this collector actually monitors.

        Collectors that don't advertise the set (e.g. ``RemoteCollector``,
        which proxies whatever the upstream agent reports) are assumed to
        serve every module.
        """
        return getattr(collector, "active_modules", VALID_MODULES)

    async def broadcast_snapshots():
        log.info("Starting background WebSocket broadcast loop")
        try:
            while True:
                if active_websockets:
                    snap = await collector.collect_async()
                    payload = json.dumps(asdict(snap), default=str)
                    disconnected = []
                    for ws in list(active_websockets):
                        try:
                            await asyncio.wait_for(ws.send_text(payload), _WS_SEND_TIMEOUT)
                        except TimeoutError:
                            log.warning("Dropping WebSocket client — send timed out")
                            disconnected.append(ws)
                        except Exception:
                            disconnected.append(ws)
                    for ws in disconnected:
                        active_websockets.discard(ws)
                        try:
                            await ws.close(code=1011, reason="Send timeout")
                        except Exception:
                            pass
                await asyncio.sleep(config.general.refresh_interval)
        except asyncio.CancelledError:
            log.info("Background WebSocket broadcast loop cancelled")
        except Exception:
            log.exception("Error in background broadcast loop")

    broadcast_task = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal broadcast_task
        broadcast_task = asyncio.create_task(broadcast_snapshots())
        yield
        if broadcast_task:
            broadcast_task.cancel()
            try:
                await broadcast_task
            except asyncio.CancelledError:
                pass
        # Only tear down a collector this app created — a shared collector
        # (e.g. owned by the TUI) must outlive the server.
        if owns_collector:
            if hasattr(collector, "close_async"):
                await collector.close_async()
            collector.close()

    app = FastAPI(
        title=title,
        version=__version__,
        description=description,
        lifespan=lifespan,
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

    # ── Security headers ────────────────────────────────────────────
    # The dashboard ships all of its own assets (Chart.js is vendored, fonts
    # are system stacks), so the CSP can forbid every external origin.
    # connect-src keeps ws:/wss: for the live stream.
    @app.middleware("http")
    async def _add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'; "
            "base-uri 'none'; "
            "form-action 'none'",
        )
        return response

    # ── API key middleware (timing-safe) ─────────────────────────────
    _skip = (skip_auth_paths or frozenset()) | frozenset({"/health"})

    if api_key:
        from fastapi.responses import JSONResponse

        @app.middleware("http")
        async def _check_api_key(request: Request, call_next):
            path = request.url.path
            is_skipped = path in _skip or any(
                path.startswith(prefix + "/") for prefix in _skip if prefix != "/"
            )
            if is_skipped:
                return await call_next(request)

            key = request.headers.get("X-API-Key")
            if not key:
                return JSONResponse(status_code=401, content={"detail": "Missing API key"})
            if not keys_match(key, api_key):
                return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
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
        if module not in _active_modules():
            raise HTTPException(
                status_code=404,
                detail=f"Module '{module}' is not enabled on this agent",
            )
        result = await collector.collect_module_async(module)
        if result is None:
            raise HTTPException(status_code=404, detail=f"No data for module '{module}'")
        if isinstance(result, list):
            serialized = [asdict(x) if hasattr(x, "__dataclass_fields__") else x for x in result]
        elif hasattr(result, "__dataclass_fields__"):
            serialized = asdict(result)
        else:
            serialized = result
        timestamp = collector._last_collected_at or time.time()
        return {"module": module, "timestamp": timestamp, "data": serialized}

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
                except TimeoutError:
                    await websocket.close(code=4001, reason="Auth timeout")
                    return
                if not keys_match(auth_msg, api_key):
                    await websocket.close(code=4001, reason="Invalid API key")
                    return

            if len(active_websockets) >= MAX_WEBSOCKET_CLIENTS:
                log.warning(
                    "Rejecting WebSocket client — %d client limit reached",
                    MAX_WEBSOCKET_CLIENTS,
                )
                await websocket.close(code=1013, reason="Too many clients")
                return

            active_websockets.add(websocket)
            initial_snap = await collector.collect_async()
            await websocket.send_text(json.dumps(asdict(initial_snap), default=str))

            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        except Exception:
            try:
                await websocket.close()
            except Exception:
                pass
        finally:
            active_websockets.discard(websocket)

    # ── Health check ─────────────────────────────────────────────────
    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "agent": "raven",
            "version": __version__,
            # Lets clients render "not monitored" instead of a misleading 0.
            "active_modules": sorted(_active_modules()),
            # Server-side default; the browser's saved preference wins.
            "theme": config.general.theme,
            # So the dashboard applies the same process limit as the TUI and
            # `raven print` rather than a hardcoded one.
            "max_display": config.processes.max_display,
        }

    return app
