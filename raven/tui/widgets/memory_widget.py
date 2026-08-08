"""Memory widget — RAM and swap usage bars with sparkline history."""

from __future__ import annotations

from collections import deque

from rich.text import Text
from textual.widgets import Static

from raven.core.models import SystemSnapshot
from raven.core.utils import color_for_percent, human_bytes, render_bar, text_sparkline


class MemoryWidget(Static):
    """Memory panel with RAM/swap bars and sparkline."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._history: deque[float] = deque(maxlen=60)

    def update_data(self, snap: SystemSnapshot) -> None:
        # See CpuWidget: history is widget state, not App state.
        mem = snap.memory
        self._history.append(mem.percent)

        text = Text()
        text.append("  Memory\n", style="bold cyan")

        # RAM bar
        text.append("  RAM   ")
        text.append_text(render_bar(mem.percent, width=20))
        text.append(f"  {human_bytes(mem.used)} / {human_bytes(mem.total)}\n", style="dim")

        # Swap bar
        if mem.swap_total > 0:
            text.append("  Swap  ")
            text.append_text(render_bar(mem.swap_percent, width=20))
            text.append(
                f"  {human_bytes(mem.swap_used)} / {human_bytes(mem.swap_total)}\n",
                style="dim",
            )

        # History sparkline
        spark = text_sparkline(self._history)
        if spark:
            text.append("  Trend ")
            text.append(spark, style=color_for_percent(mem.percent))
            text.append("\n")

        # Available
        text.append(f"  Available: {human_bytes(mem.available)}\n", style="dim")

        self.update(text)
