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
        super().__init__(config)
        from raven.config import load_config

        self._config = config or load_config()
        # Total processes seen on the last collect, before display truncation.
        self.total_count = 0

    def is_available(self) -> bool:
        return True

    # Snapshot field name → the ProcessInfo attribute to sort on, and whether
    # larger values rank first.  Mirrors ProcessTable's sort options.
    _SORT_KEYS: dict[str, tuple[str, bool]] = {
        "cpu": ("cpu_percent", True),
        "memory": ("memory_percent", True),
        "pid": ("pid", False),
        "name": ("name", False),
    }

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

        self.total_count = len(raw_procs)

        # Sort by the *configured* key before truncating.  Sorting by CPU here
        # unconditionally (as this once did) meant that with sort_by="memory" a
        # RAM-heavy but idle process could be cut before any consumer saw it.
        sort_attr, descending = self._SORT_KEYS.get(
            self._config.processes.sort_by, ("cpu_percent", True)
        )
        if sort_attr == "name":
            raw_procs.sort(key=lambda item: (item.get("name") or "").lower())
        else:
            raw_procs.sort(
                key=lambda item: (
                    item.get(sort_attr) or 0,
                    item.get("memory_percent") or 0.0,
                ),
                reverse=descending,
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
