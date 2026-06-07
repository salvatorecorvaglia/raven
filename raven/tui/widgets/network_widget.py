"""Network widget — per-interface TX/RX rates."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from raven.core.models import SystemSnapshot
from raven.core.utils import human_bytes


class NetworkWidget(Static):
    """Network panel with interface traffic."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._prev_sent: dict[str, int] = {}
        self._prev_recv: dict[str, int] = {}

    def update_data(self, snap: SystemSnapshot) -> None:
        net = snap.network
        text = Text()
        text.append("  Network\n", style="bold cyan")

        for iface in net.interfaces[:5]:
            if iface.name.startswith("lo"):
                continue

            # Calculate rates
            prev_s = self._prev_sent.get(iface.name, iface.bytes_sent)
            prev_r = self._prev_recv.get(iface.name, iface.bytes_recv)
            rate_s = max(0, iface.bytes_sent - prev_s)
            rate_r = max(0, iface.bytes_recv - prev_r)
            self._prev_sent[iface.name] = iface.bytes_sent
            self._prev_recv[iface.name] = iface.bytes_recv

            addr = iface.addrs[0] if iface.addrs else "—"
            text.append(f"  {iface.name:<10} ", style="bold")
            text.append(f"▲ {human_bytes(rate_s)}/s ", style="cyan")
            text.append(f"▼ {human_bytes(rate_r)}/s", style="green")
            text.append(f"  {addr}\n", style="dim")

        text.append(f"  Connections: {net.connections_count}\n", style="dim")
        self.update(text)
