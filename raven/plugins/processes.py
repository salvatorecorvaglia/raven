"""Process listing plugin."""

from __future__ import annotations

import psutil

from raven.config import RavenConfig
from raven.core.models import ProcessInfo
from raven.plugins.base import MonitorPlugin


class ProcessesPlugin(MonitorPlugin):
    name = "processes"
    category = "processes"

    def __init__(self, config: RavenConfig | None = None) -> None:
        super().__init__()
        self._config = config
        self._proc_cache: dict[int, psutil.Process] = {}

    def is_available(self) -> bool:
        return True

    def collect(self) -> list[ProcessInfo]:
        from raven.config import load_config

        config = self._config or load_config()
        # Retrieve at least 100 processes or twice the display count to support sorting in TUI/web
        limit = max(100, config.processes.max_display * 2)

        raw_procs = []
        current_pids = set()

        for proc in psutil.process_iter():
            pid = proc.pid
            current_pids.add(pid)
            try:
                # Reuse cached process object or cache the new one
                if pid in self._proc_cache:
                    p = self._proc_cache[pid]
                else:
                    p = proc
                    self._proc_cache[pid] = p

                # Compute CPU and memory percent. cpu_percent(interval=None) works properly
                # when reusing the same Process instance across calls.
                cpu = p.cpu_percent(interval=None)
                mem = p.memory_percent()
                raw_procs.append((p, {"pid": pid, "cpu_percent": cpu, "memory_percent": mem}))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Clean up dead processes from the cache
        dead_pids = set(self._proc_cache.keys()) - current_pids
        for pid in dead_pids:
            self._proc_cache.pop(pid, None)

        # Sort by CPU and memory usage to identify top active processes
        raw_procs.sort(
            key=lambda item: (
                item[1].get("cpu_percent") or 0.0,
                item[1].get("memory_percent") or 0.0,
            ),
            reverse=True,
        )

        top_procs = raw_procs[:limit]
        procs: list[ProcessInfo] = []

        for proc, info in top_procs:
            try:
                # Fetch detailed heavy attributes only for top processes
                full_info = proc.as_dict(
                    attrs=["name", "username", "status", "cmdline", "num_threads", "memory_info"]
                )
                cmdline = full_info.get("cmdline") or []
                mem_info = full_info.get("memory_info")
                procs.append(
                    ProcessInfo(
                        pid=info.get("pid", 0),
                        name=full_info.get("name") or "",
                        username=full_info.get("username") or "",
                        cpu_percent=info.get("cpu_percent", 0.0) or 0.0,
                        memory_percent=round(info.get("memory_percent", 0.0) or 0.0, 1),
                        status=full_info.get("status") or "",
                        cmdline=" ".join(cmdline) if cmdline else "",
                        num_threads=full_info.get("num_threads", 0) or 0,
                        memory_rss=mem_info.rss if mem_info else 0,
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return procs


PLUGIN_INFO = {
    "name": "processes",
    "category": "processes",
    "class": ProcessesPlugin,
}
