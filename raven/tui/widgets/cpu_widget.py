"""CPU widget — overall usage, per-core bars, frequency, sparkline history."""

from __future__ import annotations

from collections import deque

from rich.text import Text
from textual.widgets import Static

from raven.core.models import SystemSnapshot
from raven.core.utils import color_for_percent, text_sparkline


def _bar(pct: float, width: int = 15) -> Text:
    filled = int(width * pct / 100)
    color = color_for_percent(pct)
    t = Text()
    t.append("█" * filled, style=color)
    t.append("░" * (width - filled), style="dim")
    t.append(f" {pct:5.1f}%", style=f"bold {color}")
    return t


class CpuWidget(Static):
    """CPU panel with per-core bars and sparkline."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._history: deque[float] = deque(maxlen=60)

    def update_data(self, snap: SystemSnapshot) -> None:
        cpu = snap.cpu
        self._history.append(cpu.percent_overall)

        text = Text()
        text.append("  CPU\n", style="bold cyan")

        # Overall bar
        text.append("  Overall  ")
        text.append_text(_bar(cpu.percent_overall))
        text.append("\n")

        # Per-core bars (compact: 2 or 4 per line depending on core count)
        cores = cpu.percent_per_core
        cols = 4 if len(cores) > 16 else 2
        bar_width = 6 if cols == 4 else 10
        for i in range(0, len(cores), cols):
            line = Text("  ")
            for j in range(cols):
                idx = i + j
                if idx < len(cores):
                    line.append(f"C{idx:<2} ")
                    line.append_text(_bar(cores[idx], width=bar_width))
                    line.append("  ")
            text.append_text(line)
            text.append("\n")

        # Frequency and load
        info_parts: list[str] = []
        if cpu.frequency_current_mhz:
            info_parts.append(f"Freq: {cpu.frequency_current_mhz:.0f} MHz")
        if cpu.load_avg_1 is not None:
            info_parts.append(
                f"Load: {cpu.load_avg_1:.2f} {cpu.load_avg_5:.2f} {cpu.load_avg_15:.2f}"
            )
        if info_parts:
            text.append("  " + "  │  ".join(info_parts) + "\n", style="dim")

        # Mini sparkline
        spark = text_sparkline(self._history)
        if spark:
            text.append(f"  {spark}\n", style=color_for_percent(cpu.percent_overall))

        self.update(text)
