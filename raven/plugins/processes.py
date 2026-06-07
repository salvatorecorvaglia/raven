"""Process listing plugin."""

from __future__ import annotations

import psutil

from raven.core.models import ProcessInfo
from raven.plugins.base import MonitorPlugin


class ProcessesPlugin(MonitorPlugin):
    name = "processes"
    category = "processes"

    def is_available(self) -> bool:
        return True

    def collect(self) -> list[ProcessInfo]:
        from raven.config import load_config
        config = load_config()
        # Retrieve at least 100 processes or twice the display count to support sorting in TUI/web
        limit = max(100, config.processes.max_display * 2)

        raw_procs = []
        for proc in psutil.process_iter(attrs=["pid", "cpu_percent", "memory_percent"]):
            try:
                raw_procs.append((proc, proc.info))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Sort by CPU and memory usage to identify top active processes
        raw_procs.sort(
            key=lambda item: (
                item[1].get("cpu_percent") or 0.0,
                item[1].get("memory_percent") or 0.0
            ),
            reverse=True
        )

        top_procs = raw_procs[:limit]
        procs: list[ProcessInfo] = []

        for proc, info in top_procs:
            try:
                # Fetch detailed heavy attributes only for top processes
                full_info = proc.as_dict(attrs=[
                    "name", "username", "status", "cmdline",
                    "num_threads", "memory_info"
                ])
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
