"""Central metric collection orchestrator.

The ``Collector`` loads all enabled plugins once, then on each ``collect()``
call runs every plugin and assembles a ``SystemSnapshot``.
"""

from __future__ import annotations

import asyncio
import atexit
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from raven.config import RavenConfig, load_config
from raven.core.models import (
    ContainerMetrics,
    CpuMetrics,
    DiskMetrics,
    MemoryMetrics,
    NetworkMetrics,
    SensorMetrics,
    SystemInfoMetrics,
    SystemSnapshot,
)
from raven.core.plugin_manager import get_enabled_plugins

log = logging.getLogger(__name__)


class Collector:
    """Collects system metrics from all enabled plugins."""

    def __init__(self, config: RavenConfig | None = None) -> None:
        self.config = config or load_config()
        self.plugins = get_enabled_plugins(self.config)
        # Instance-level executor — properly cleaned up on shutdown
        self._executor = ThreadPoolExecutor(
            max_workers=min(len(self.plugins), 8) or 1,
            thread_name_prefix="raven-collector",
        )
        atexit.register(self._shutdown)
        log.info(
            "Collector initialised with %d plugins: %s",
            len(self.plugins),
            [p.name for p in self.plugins],
        )

    def _shutdown(self) -> None:
        """Shut down the thread pool on interpreter exit."""
        self._executor.shutdown(wait=False)

    def close(self) -> None:
        """Explicitly shut down the executor and unregister from atexit to prevent leaks."""
        try:
            atexit.unregister(self._shutdown)
        except Exception:
            pass
        self._shutdown()

    def collect(self) -> SystemSnapshot:
        """Run all plugins in parallel and return a snapshot."""
        results: dict[str, Any] = {}
        futures = {self._executor.submit(plugin.collect): plugin for plugin in self.plugins}
        for future in as_completed(futures):
            plugin = futures[future]
            try:
                results[plugin.name] = future.result(timeout=10)
            except Exception:
                log.exception("Plugin %s failed during collection", plugin.name)

        return self._assemble(results)

    async def collect_async(self) -> SystemSnapshot:
        """Run collection in a thread executor (non-blocking for async apps)."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.collect)

    # ── private ──────────────────────────────────────────────────────────

    @staticmethod
    def _assemble(results: dict[str, Any]) -> SystemSnapshot:
        """Map plugin results to the ``SystemSnapshot`` fields.

        Note: processes are NOT sorted here — consumers (TUI, web, exporters)
        apply their own sort based on the user's ``config.processes.sort_by``.
        """
        procs = results.get("processes", [])
        if not isinstance(procs, list):
            procs = []

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
