"""Abstract base class for Raven monitoring plugins.

Every plugin must subclass ``MonitorPlugin`` and implement ``collect()``
and ``is_available()``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from raven.config import RavenConfig


class MonitorPlugin(ABC):
    """Base class for all monitoring plugins."""

    name: str = "unnamed"
    category: str = "general"

    def __init__(self, config: RavenConfig | None = None) -> None:
        """Every plugin accepts the config, whether or not it uses it.

        A uniform signature lets ``get_enabled_plugins`` construct plugins
        without inspecting each constructor to guess what it accepts.
        """
        self.config = config

    @abstractmethod
    def collect(self) -> Any:
        """Collect and return a metric dataclass."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this plugin can operate on the current platform."""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
