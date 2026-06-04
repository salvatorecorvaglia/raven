"""Central metric collection orchestrator.

The ``Collector`` loads all enabled plugins once, then on each ``collect()``
call runs every plugin and assembles a ``SystemSnapshot``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from raven.config import RavenConfig, load_config
from raven.core.models import (
    ContainerMetrics,
    CpuMetrics,
    DiskMetrics,
    MemoryMetrics,
    NetworkMetrics,
    ProcessInfo,
    SensorMetrics,
    SystemInfoMetrics,
    SystemSnapshot,
    UserInfo,
)
from raven.core.plugin_manager import get_enabled_plugins
from raven.plugins.base import MonitorPlugin

log = logging.getLogger(__name__)

# Thread pool for running blocking psutil calls off the event loop
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="raven-collector")


class Collector:
    """Collects system metrics from all enabled plugins."""

    def __init__(self, config: RavenConfig | None = None) -> None:
        self.config = config or load_config()
        self.plugins = get_enabled_plugins(self.config)
        log.info(
            "Collector initialised with %d plugins: %s",
            len(self.plugins),
            [p.name for p in self.plugins],
        )

    def collect(self) -> SystemSnapshot:
        """Run all plugins synchronously and return a snapshot."""
        results: dict[str, Any] = {}
        for plugin in self.plugins:
            try:
                results[plugin.name] = plugin.collect()
            except Exception:
                log.exception("Plugin %s failed during collection", plugin.name)

        return self._assemble(results)

    async def collect_async(self) -> SystemSnapshot:
        """Run collection in a thread executor (non-blocking for async apps)."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_executor, self.collect)

    # ── private ──────────────────────────────────────────────────────────

    @staticmethod
    def _assemble(results: dict[str, Any]) -> SystemSnapshot:
        """Map plugin results to the ``SystemSnapshot`` fields."""
        # Sort processes by CPU usage descending
        procs = results.get("processes", [])
        if isinstance(procs, list):
            procs = sorted(procs, key=lambda p: p.cpu_percent, reverse=True)

        return SystemSnapshot(
            timestamp=time.time(),
            cpu=results.get("cpu", CpuMetrics()),
            memory=results.get("memory", MemoryMetrics()),
            disk=results.get("disk", DiskMetrics()),
            network=results.get("network", NetworkMetrics()),
            processes=procs,
            users=results.get("users", []),
            sensors=results.get("sensors", SensorMetrics()),
            containers=results.get("containers", ContainerMetrics()),
            system_info=results.get("system_info", SystemInfoMetrics()),
        )
