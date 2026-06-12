"""Abstract base class for Raven monitoring plugins.

Every plugin must subclass ``MonitorPlugin`` and implement ``collect()``
and ``is_available()``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MonitorPlugin(ABC):
    """Base class for all monitoring plugins."""

    name: str = "unnamed"
    category: str = "general"

    @abstractmethod
    def collect(self) -> Any:
        """Collect and return a metric dataclass."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this plugin can operate on the current platform."""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
