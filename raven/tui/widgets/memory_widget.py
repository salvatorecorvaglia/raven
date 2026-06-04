"""Memory widget — RAM and swap usage bars with sparkline history."""

from __future__ import annotations

from collections import deque

from rich.text import Text
from textual.widgets import Static

from raven.core.models import SystemSnapshot


def _human_bytes(n: int | float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _color_for_pct(pct: float) -> str:
    if pct < 50:
        return "green"
    elif pct < 80:
        return "yellow"
    return "red"


def _bar(pct: float, width: int = 20) -> Text:
    filled = int(width * pct / 100)
    color = _color_for_pct(pct)
    t = Text()
    t.append("█" * filled, style=color)
    t.append("░" * (width - filled), style="dim")
    t.append(f" {pct:5.1f}%", style=f"bold {color}")
    return t


class MemoryWidget(Static):
    """Memory panel with RAM/swap bars and sparkline."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._history: deque[float] = deque(maxlen=60)

    def update_data(self, snap: SystemSnapshot) -> None:
        mem = snap.memory
        self._history.append(mem.percent)

        text = Text()
        text.append("  Memory\n", style="bold cyan")

        # RAM bar
        text.append("  RAM   ")
        text.append_text(_bar(mem.percent))
        text.append(f"  {_human_bytes(mem.used)} / {_human_bytes(mem.total)}\n", style="dim")

        # Swap bar
        if mem.swap_total > 0:
            text.append("  Swap  ")
            text.append_text(_bar(mem.swap_percent))
            text.append(
                f"  {_human_bytes(mem.swap_used)} / {_human_bytes(mem.swap_total)}\n",
                style="dim",
            )

        # Available
        text.append(f"  Available: {_human_bytes(mem.available)}\n", style="dim")

        # Sparkline
        if len(self._history) > 1:
            spark_chars = "▁▂▃▄▅▆▇█"
            max_val = max(self._history) or 1
            spark = ""
            for v in self._history:
                idx = int(v / max_val * (len(spark_chars) - 1))
                spark += spark_chars[min(idx, len(spark_chars) - 1)]
            text.append(f"  {spark}\n", style=_color_for_pct(mem.percent))

        self.update(text)
