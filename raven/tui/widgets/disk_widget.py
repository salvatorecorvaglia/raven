"""Disk widget — partition usage bars and I/O stats."""

from __future__ import annotations

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
    if pct < 60:
        return "green"
    elif pct < 85:
        return "yellow"
    return "red"


class DiskWidget(Static):
    """Disk panel with per-partition usage and I/O."""

    def update_data(self, snap: SystemSnapshot) -> None:
        disk = snap.disk
        text = Text()
        text.append("  Disk\n", style="bold cyan")

        for dp in disk.partitions[:6]:
            color = _color_for_pct(dp.percent)
            filled = int(12 * dp.percent / 100)
            bar = "█" * filled + "░" * (12 - filled)

            text.append(f"  {dp.mountpoint:<14} ", style="")
            text.append(bar, style=color)
            text.append(f" {dp.percent:5.1f}%", style=f"bold {color}")
            text.append(f"  {_human_bytes(dp.used)}/{_human_bytes(dp.total)}\n", style="dim")

        # I/O
        io = disk.io
        text.append(
            f"  I/O  Read: {_human_bytes(io.read_bytes)}  "
            f"Write: {_human_bytes(io.write_bytes)}\n",
            style="dim",
        )

        self.update(text)
