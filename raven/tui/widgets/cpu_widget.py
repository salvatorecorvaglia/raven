"""CPU widget — overall usage, per-core bars, frequency, sparkline history."""

from __future__ import annotations

from collections import deque

from rich.text import Text
from textual.widgets import Static, Sparkline

from raven.core.models import SystemSnapshot


def _color_for_pct(pct: float) -> str:
    if pct < 50:
        return "green"
    elif pct < 80:
        return "yellow"
    return "red"


def _bar(pct: float, width: int = 15) -> Text:
    filled = int(width * pct / 100)
    color = _color_for_pct(pct)
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

        # Per-core bars (compact: 2 per line)
        cores = cpu.percent_per_core
        for i in range(0, len(cores), 2):
            line = Text("  ")
            for j in range(2):
                idx = i + j
                if idx < len(cores):
                    line.append(f"C{idx:<2} ")
                    line.append_text(_bar(cores[idx], width=10))
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

        # Mini sparkline (text-based since we can't nest widgets easily)
        if len(self._history) > 1:
            spark_chars = "▁▂▃▄▅▆▇█"
            max_val = max(self._history) or 1
            spark = ""
            for v in self._history:
                idx = int(v / max_val * (len(spark_chars) - 1))
                spark += spark_chars[min(idx, len(spark_chars) - 1)]
            text.append(f"  {spark}\n", style=_color_for_pct(cpu.percent_overall))

        self.update(text)
