"""Header widget — hostname, OS, uptime, clock."""

from __future__ import annotations

import datetime

from rich.text import Text
from textual.widgets import Static

from raven.core.models import SystemSnapshot


class HeaderWidget(Static):
    """Top bar showing system identity and time."""

    def update_data(self, snap: SystemSnapshot) -> None:
        si = snap.system_info
        uptime = str(datetime.timedelta(seconds=int(si.uptime_seconds)))
        now = datetime.datetime.now().strftime("%H:%M:%S")

        text = Text()
        text.append("  🐦‍⬛ RAVEN", style="bold bright_white")
        text.append("  │  ", style="dim")
        text.append(f"{si.hostname}", style="bold cyan")
        text.append(f"  │  {si.os_name} {si.os_version} ({si.architecture})", style="")
        text.append(f"  │  ⏱ {uptime}", style="")
        text.append(f"  │  🕐 {now}", style="bold")

        self.update(text)
