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
        procs: list[ProcessInfo] = []
        attrs = [
            "pid", "name", "username", "cpu_percent",
            "memory_percent", "status", "cmdline",
            "num_threads", "memory_info",
        ]
        for proc in psutil.process_iter(attrs=attrs):
            try:
                info = proc.info
                cmdline = info.get("cmdline") or []
                mem_info = info.get("memory_info")
                procs.append(
                    ProcessInfo(
                        pid=info.get("pid", 0),
                        name=info.get("name", "") or "",
                        username=info.get("username", "") or "",
                        cpu_percent=info.get("cpu_percent", 0.0) or 0.0,
                        memory_percent=round(info.get("memory_percent", 0.0) or 0.0, 1),
                        status=info.get("status", "") or "",
                        cmdline=" ".join(cmdline) if cmdline else "",
                        num_threads=info.get("num_threads", 0) or 0,
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
