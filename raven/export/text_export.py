"""Plain-text (Rich-formatted) export."""

from __future__ import annotations

import datetime

from rich.console import Console

from raven.core.models import SystemSnapshot
from raven.core.utils import human_bytes
from raven.export.base import BaseExporter


def _bar(percent: float, width: int = 20) -> str:
    """Simple ASCII bar for a percentage."""
    filled = int(width * percent / 100)
    return f"[{'█' * filled}{'░' * (width - filled)}] {percent:.1f}%"


class TextExporter(BaseExporter):
    name = "text"

    def format(self, snapshot: SystemSnapshot, modules: list[str] | None = None) -> str:
        Console(file=None, force_terminal=True, width=100)
        parts: list[str] = []

        show_all = modules is None
        mods = set(modules or [])

        # ── System Info ──────────────────────────────────────────────
        if show_all or "system_info" in mods:
            si = snapshot.system_info
            uptime = str(datetime.timedelta(seconds=int(si.uptime_seconds)))
            parts.append(
                f"  Host: {si.hostname}  |  OS: {si.os_name} {si.os_version}  |"
                f"  Kernel: {si.kernel}  |  Arch: {si.architecture}  |  Uptime: {uptime}"
            )
            parts.append("")

        # ── CPU ──────────────────────────────────────────────────────
        if show_all or "cpu" in mods:
            c = snapshot.cpu
            parts.append(f"  CPU  {_bar(c.percent_overall)}  {c.core_count_logical} cores")
            if c.frequency_current_mhz:
                parts[-1] += f"  @ {c.frequency_current_mhz:.0f} MHz"
            if c.load_avg_1 is not None:
                parts.append(f"  Load: {c.load_avg_1:.2f}  {c.load_avg_5:.2f}  {c.load_avg_15:.2f}")
            parts.append("")

        # ── Memory ───────────────────────────────────────────────────
        if show_all or "memory" in mods:
            m = snapshot.memory
            parts.append(
                f"  RAM  {_bar(m.percent)}  {human_bytes(m.used)} / {human_bytes(m.total)}"
            )
            if m.swap_total > 0:
                parts.append(
                    f"  Swap {_bar(m.swap_percent)}"
                    f"  {human_bytes(m.swap_used)} / {human_bytes(m.swap_total)}"
                )
            parts.append("")

        # ── Disk ─────────────────────────────────────────────────────
        if show_all or "disk" in mods:
            for dp in snapshot.disk.partitions[:8]:
                parts.append(
                    f"  {dp.mountpoint:<15} {_bar(dp.percent)}"
                    f"  {human_bytes(dp.used)} / {human_bytes(dp.total)}"
                )
            io = snapshot.disk.io
            parts.append(
                f"  I/O  R: {human_bytes(io.read_bytes)}  W: {human_bytes(io.write_bytes)}"
            )
            parts.append("")

        # ── Network ──────────────────────────────────────────────────
        if show_all or "network" in mods:
            for iface in snapshot.network.interfaces[:6]:
                addr_str = ", ".join(iface.addrs[:2]) if iface.addrs else "—"
                parts.append(
                    f"  {iface.name:<12} ▲ {human_bytes(iface.bytes_sent)}"
                    f"  ▼ {human_bytes(iface.bytes_recv)}  ({addr_str})"
                )
            parts.append(f"  Connections: {snapshot.network.connections_count}")
            parts.append("")

        # ── Processes ────────────────────────────────────────────────
        if show_all or "processes" in mods:
            parts.append("  PID       CPU%   MEM%   Name")
            parts.append("  " + "─" * 50)
            for p in snapshot.processes[:15]:
                parts.append(
                    f"  {p.pid:<9} {p.cpu_percent:5.1f}  {p.memory_percent:5.1f}   {p.name[:30]}"
                )
            parts.append("")

        # ── Users ────────────────────────────────────────────────────
        if show_all or "users" in mods:
            if snapshot.users:
                user_strs = [f"{u.name}({u.terminal or '?'})" for u in snapshot.users]
                parts.append(f"  Users: {', '.join(user_strs)}")
                parts.append("")

        # ── Sensors ──────────────────────────────────────────────────
        if show_all or "sensors" in mods:
            if snapshot.sensors.temperatures:
                temp_strs = [
                    f"{t.label}: {t.current:.0f}°C" for t in snapshot.sensors.temperatures[:8]
                ]
                parts.append(f"  Temps: {', '.join(temp_strs)}")
            if snapshot.sensors.fans:
                fan_strs = [f"{f.label}: {f.current} RPM" for f in snapshot.sensors.fans[:4]]
                parts.append(f"  Fans: {', '.join(fan_strs)}")
            if snapshot.sensors.battery:
                bat = snapshot.sensors.battery
                plugged = "⚡" if bat.power_plugged else "🔋"
                parts.append(f"  Battery: {bat.percent:.0f}% {plugged}")
            if snapshot.sensors.temperatures or snapshot.sensors.fans or snapshot.sensors.battery:
                parts.append("")

        # ── Containers ───────────────────────────────────────────────
        if show_all or "containers" in mods:
            if snapshot.containers.containers:
                parts.append("  Containers:")
                for ct in snapshot.containers.containers[:10]:
                    parts.append(f"    [{ct.runtime}] {ct.name:<25} {ct.status:<12} {ct.image}")
                parts.append("")

        return "\n".join(parts)
