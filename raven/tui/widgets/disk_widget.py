"""Disk widget — partition usage bars and I/O stats."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from raven.core.models import SystemSnapshot
from raven.core.utils import color_for_percent, human_bytes


class DiskWidget(Static):
    """Disk panel with per-partition usage and I/O."""

    def update_data(self, snap: SystemSnapshot) -> None:
        disk = snap.disk
        text = Text()
        text.append("  Disk\n", style="bold cyan")

        for dp in disk.partitions[:6]:
            color = color_for_percent(dp.percent, thresholds=(60.0, 85.0))
            filled = int(12 * dp.percent / 100)
            bar = "█" * filled + "░" * (12 - filled)

            mount_truncated = dp.mountpoint[:14]
            text.append(f"  {mount_truncated:<14} ", style="")
            text.append(bar, style=color)
            text.append(f" {dp.percent:5.1f}%", style=f"bold {color}")
            text.append(f"  {human_bytes(dp.used)}/{human_bytes(dp.total)}\n", style="dim")

        # I/O
        io = disk.io
        text.append(
            f"  I/O  Read: {human_bytes(io.read_bytes)}  Write: {human_bytes(io.write_bytes)}\n",
            style="dim",
        )

        self.update(text)
