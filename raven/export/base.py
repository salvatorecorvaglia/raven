"""Abstract base class for export formatters."""

from __future__ import annotations

from abc import ABC, abstractmethod

from raven.core.models import SystemSnapshot


class BaseExporter(ABC):
    """Format a ``SystemSnapshot`` as a string in a given format."""

    name: str = "base"

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
