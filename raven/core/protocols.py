"""Protocol defining the collector interface.

Both the local ``Collector`` and ``RemoteCollector`` implement this
protocol so that TUI, web, and exporters can work with either seamlessly.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from raven.core.models import SystemSnapshot


@runtime_checkable
class MetricCollector(Protocol):
    """Interface that all metric collectors must satisfy."""

    def collect(self) -> SystemSnapshot:
        """Run a synchronous collection and return a snapshot."""
        ...

    async def collect_async(self) -> SystemSnapshot:
        """Run an async collection and return a snapshot."""
        ...

    def close(self) -> None:
        """Clean up synchronous collector resources."""
        ...

    async def close_async(self) -> None:
        """Clean up asynchronous collector resources."""
        ...
