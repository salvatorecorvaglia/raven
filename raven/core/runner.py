"""Runner helper to spawn background servers for Web and Remote agents.

Decouples CLI/TUI routing from uvicorn thread spawning.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

import uvicorn

from raven.config import RavenConfig

if TYPE_CHECKING:
    from raven.core.collector import Collector

log = logging.getLogger(__name__)


def start_background_servers(config: RavenConfig, collector: Collector | None = None) -> None:
    """Start web and/or remote servers in background daemon threads if configured."""
    if config.web.enabled:
        from raven.web.server import create_app

        web_app = create_app(config, collector=collector)
        t = threading.Thread(
            target=uvicorn.run,
            args=(web_app,),
            kwargs={
                "host": config.web.host,
                "port": config.web.port,
                "log_level": "warning",
                "install_signal_handlers": False,
            },
            daemon=True,
        )
        t.start()
        log.info(
            "Started background Web server thread on http://%s:%d",
            config.web.host,
            config.web.port,
        )

    if config.remote.enabled:
        from raven.remote.server import create_remote_app

        remote_app = create_remote_app(config, collector=collector)
        t = threading.Thread(
            target=uvicorn.run,
            args=(remote_app,),
            kwargs={
                "host": config.remote.host,
                "port": config.remote.port,
                "log_level": "warning",
                "install_signal_handlers": False,
            },
            daemon=True,
        )
        t.start()
        log.info(
            "Started background Remote agent thread on http://%s:%d",
            config.remote.host,
            config.remote.port,
        )
