"""Abstract base class for export formatters."""

from __future__ import annotations

from abc import ABC, abstractmethod

from raven.config import RavenConfig
from raven.core.models import SystemSnapshot


class BaseExporter(ABC):
    """Format a ``SystemSnapshot`` as a string in a given format."""

    name: str = "base"

    def __init__(self, config: RavenConfig | None = None) -> None:
        # Exporters honour processes.max_display / processes.sort_by, so the
        # same limits apply to `raven print` as to the TUI.
        self.config = config or RavenConfig()

    def sorted_processes(self, snapshot: SystemSnapshot) -> list:
        """Processes sorted by ``processes.sort_by`` and capped at ``max_display``."""
        sort_map = {
            "cpu": ("cpu_percent", True),
            "memory": ("memory_percent", True),
            "pid": ("pid", False),
            "name": ("name", False),
        }
        key, reverse = sort_map.get(self.config.processes.sort_by, ("cpu_percent", True))
        procs = sorted(
            snapshot.processes,
            key=lambda p: (getattr(p, key, 0) or 0) if key != "name" else (p.name or "").lower(),
            reverse=reverse,
        )
        return procs[: self.config.processes.max_display]

    @abstractmethod
    def format(self, snapshot: SystemSnapshot, modules: list[str] | None = None) -> str:
        """Return the snapshot formatted as a string.

        Parameters
        ----------
        snapshot:
            The collected metrics.
        modules:
            Optional list of module names to include.  ``None`` = all.
        """
