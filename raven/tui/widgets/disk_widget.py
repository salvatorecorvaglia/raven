"""Disk widget — partition usage bars and I/O stats."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from raven.core.models import SystemSnapshot
from raven.core.utils import human_bytes, render_bar
from raven.tui.widgets._common import section_header


class DiskWidget(Static):
    """Disk panel with per-partition usage and I/O."""

    def update_data(self, snap: SystemSnapshot) -> None:
        disk = snap.disk
        text = Text()
        section_header(text, "Disk")

        for dp in disk.partitions[:6]:
            mount_truncated = dp.mountpoint[:14]
            text.append(f"  {mount_truncated:<14} ", style="")
            text.append_text(render_bar(dp.percent, width=12))
            text.append(f"  {human_bytes(dp.used)}/{human_bytes(dp.total)}\n", style="dim")

        # I/O
        io = disk.io
        text.append(
            f"  I/O  Read: {human_bytes(io.read_bytes)}  Write: {human_bytes(io.write_bytes)}\n",
            style="dim",
        )

        self.update(text)
