"""Raven TUI — full-screen Textual dashboard.

Keybindings:
    q / ctrl-c  Quit
    r           Force refresh
    p           Cycle process sort (cpu → memory → pid → name)
"""

from __future__ import annotations

import logging
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Footer

from raven.config import RavenConfig
from raven.core.collector import Collector
from raven.core.models import SystemSnapshot
from raven.core.protocols import MetricCollector
from raven.tui.widgets.container_widget import ContainerWidget
from raven.tui.widgets.cpu_widget import CpuWidget
from raven.tui.widgets.disk_widget import DiskWidget
from raven.tui.widgets.header_widget import HeaderWidget
from raven.tui.widgets.memory_widget import MemoryWidget
from raven.tui.widgets.network_widget import NetworkWidget
from raven.tui.widgets.process_table import ProcessTable
from raven.tui.widgets.sensor_widget import SensorWidget

log = logging.getLogger(__name__)

# Sort cycle for processes
_SORT_CYCLE = ["cpu", "memory", "pid", "name"]

CSS_PATH = Path(__file__).parent / "dashboard.tcss"


class RavenApp(App):
    """Raven system monitor TUI application."""

    TITLE = "🐦‍⬛ Raven System Monitor"
    CSS_PATH = CSS_PATH

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("r", "refresh", "Refresh"),
        Binding("p", "cycle_sort", "Sort procs"),
    ]

    def __init__(
        self,
        collector: MetricCollector | None = None,
        config: RavenConfig | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        from raven.config import load_config

        self._config = config or load_config()
        self._collector: MetricCollector = collector or Collector(self._config)
        sort_by = self._config.processes.sort_by
        if sort_by in _SORT_CYCLE:
            self._sort_index = _SORT_CYCLE.index(sort_by)
        else:
            self._sort_index = 0

    def compose(self) -> ComposeResult:
        with Container(id="dashboard"):
            yield HeaderWidget(id="raven-header")
            yield CpuWidget(id="cpu-panel")
            yield MemoryWidget(id="memory-panel")
            yield ProcessTable(id="process-panel")
            yield DiskWidget(id="disk-panel")
            yield NetworkWidget(id="network-panel")
            yield SensorWidget(id="sensor-panel")
            yield ContainerWidget(id="container-panel")
        yield Footer()

    def on_mount(self) -> None:
        """Start the periodic refresh timer."""
        interval = self._config.general.refresh_interval
        self.set_interval(interval, self._tick)
        # Do an initial collection immediately
        self._tick()

    def _tick(self) -> None:
        """Collect metrics and push to all widgets."""
        self.run_worker(self._async_tick, exclusive=True)

    async def _async_tick(self) -> None:
        try:
            snap = await self._collector.collect_async()
            self._update_widgets(snap)
        except Exception:
            log.exception("Metric collection failed")
            self.notify("⚠ Collection failed — data may be stale", severity="warning")

    def _update_widgets(self, snap: SystemSnapshot) -> None:
        """Push a snapshot to all dashboard widgets."""
        header: HeaderWidget = self.query_one("#raven-header", HeaderWidget)
        header.update_data(snap)

        cpu: CpuWidget = self.query_one("#cpu-panel", CpuWidget)
        cpu.update_data(snap)

        mem: MemoryWidget = self.query_one("#memory-panel", MemoryWidget)
        mem.update_data(snap)

        disk: DiskWidget = self.query_one("#disk-panel", DiskWidget)
        disk.update_data(snap)

        net: NetworkWidget = self.query_one("#network-panel", NetworkWidget)
        net.update_data(snap, refresh_interval=self._config.general.refresh_interval)

        sensor: SensorWidget = self.query_one("#sensor-panel", SensorWidget)
        sensor.update_data(snap)

        container: ContainerWidget = self.query_one("#container-panel", ContainerWidget)
        container.update_data(snap)

        proc: ProcessTable = self.query_one("#process-panel", ProcessTable)
        sort_by = _SORT_CYCLE[self._sort_index]
        proc.update_data(
            snap,
            max_display=self._config.processes.max_display,
            sort_by=sort_by,
        )

    # ── Actions ──────────────────────────────────────────────────────

    def action_refresh(self) -> None:
        self._tick()

    def action_cycle_sort(self) -> None:
        self._sort_index = (self._sort_index + 1) % len(_SORT_CYCLE)
        self.notify(f"Sorting processes by: {_SORT_CYCLE[self._sort_index]}")
        self._tick()

    def on_unmount(self) -> None:
        """Teardown the collector on app exit."""
        self._collector.close()
