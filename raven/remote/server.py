"""Remote monitoring agent — runs on a monitored host.

Exposes the same REST API endpoints so that a remote client (or the
TUI / web dashboard) can connect and pull metrics.

Usage::

    raven serve --host 0.0.0.0 --port 9090
"""

from __future__ import annotations

from fastapi import FastAPI

from raven.config import RavenConfig, load_config
from raven.core.api import create_base_app, warn_open_bind
from raven.core.collector import Collector


def create_remote_app(
    config: RavenConfig | None = None,
    collector: Collector | None = None,
) -> FastAPI:
    """Create the remote agent FastAPI application."""
    cfg = config or load_config()
    # An injected collector is shared with another consumer (e.g. the TUI), so
    # this app must not shut it down — see ``owns_collector``.
    owns_collector = collector is None
    collector = collector or Collector(cfg)
    api_key = cfg.remote.api_key

    warn_open_bind(cfg.remote.host, api_key, "Remote agent")

    return create_base_app(
        config=cfg,
        collector=collector,
        title="Raven Remote Agent",
        description="Remote system monitoring agent",
        api_key=api_key,
        owns_collector=owns_collector,
    )
