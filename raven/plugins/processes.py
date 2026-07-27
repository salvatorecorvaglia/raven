"""Process listing plugin."""

from __future__ import annotations

import logging

import psutil

from raven.config import RavenConfig
from raven.core.models import ProcessInfo
from raven.plugins.base import MonitorPlugin

log = logging.getLogger(__name__)


class ProcessesPlugin(MonitorPlugin):
    name = "processes"
    category = "processes"

    def __init__(self, config: RavenConfig | None = None) -> None:
        super().__init__()
        from raven.config import load_config

        self._config = config or load_config()

    def is_available(self) -> bool:
        return True

    def collect(self) -> list[ProcessInfo]:
        limit = max(100, self._config.processes.max_display * 2)

        attrs = [
            "pid",
            "name",
            "username",
            "cpu_percent",
            "memory_percent",
            "status",
            "cmdline",
            "num_threads",
            "memory_info",
        ]

        raw_procs: list[dict] = []
        try:
            for proc in psutil.process_iter(attrs=attrs):
                try:
                    info = proc.info
                    if info and info.get("pid") is not None:
                        raw_procs.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            log.debug("Process iteration encountered error", exc_info=True)

        raw_procs.sort(
            key=lambda item: (
                item.get("cpu_percent") or 0.0,
                item.get("memory_percent") or 0.0,
            ),
            reverse=True,
        )

        procs: list[ProcessInfo] = []
        for info in raw_procs[:limit]:
            cmdline = info.get("cmdline") or []
            mem_info = info.get("memory_info")
            procs.append(
                ProcessInfo(
                    pid=info.get("pid", 0) or 0,
                    name=info.get("name") or "",
                    username=info.get("username") or "",
                    cpu_percent=round(info.get("cpu_percent", 0.0) or 0.0, 1),
                    memory_percent=round(info.get("memory_percent", 0.0) or 0.0, 1),
                    status=info.get("status") or "",
                    cmdline=" ".join(cmdline) if cmdline else "",
                    num_threads=info.get("num_threads", 0) or 0,
                    memory_rss=mem_info.rss if mem_info else 0,
                )
            )
        return procs

