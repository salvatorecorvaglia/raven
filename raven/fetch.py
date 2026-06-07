"""Quick-fetch command — neofetch-style system summary.

Usage::

    raven fetch
"""

from __future__ import annotations

import datetime

from rich.console import Console
from rich.panel import Panel

from raven.config import RavenConfig
from raven.core.collector import Collector
from raven.core.utils import human_bytes

# ── ASCII Art ────────────────────────────────────────────────────────────────

_RAVEN_ART = r"""
       ▄▄▄
      ▀█▀██▄
       ▀█▄███▄
        ██████▄
        ████████
       ▄█▀ █████
      ▄██   ▀████
     ████    ▀███
    █████     ███▌
   ▐████      ██▌
    ▀▀██▄    ▄██
       ▀▀▄▄▄▀▀
"""


def _color_percent(percent: float) -> str:
    """Return a colored percentage string."""
    if percent < 50:
        return f"[green]{percent:.1f}%[/green]"
    elif percent < 80:
        return f"[yellow]{percent:.1f}%[/yellow]"
    else:
        return f"[red]{percent:.1f}%[/red]"


def run_fetch(config: RavenConfig | None = None) -> None:
    """Print a quick system summary to the console."""
    console = Console()
    collector = Collector(config)
    snap = collector.collect()

    si = snap.system_info
    cpu = snap.cpu
    mem = snap.memory
    disk = snap.disk
    net = snap.network
    sensors = snap.sensors
    containers = snap.containers

    uptime = str(datetime.timedelta(seconds=int(si.uptime_seconds)))

    # Build info lines
    lines: list[str] = []
    lines.append(f"[bold cyan]{si.username}[/bold cyan]@[bold cyan]{si.hostname}[/bold cyan]")
    lines.append(f"[dim]{'─' * 30}[/dim]")
    lines.append(f"[bold]OS[/bold]       {si.os_name} {si.os_version} ({si.architecture})")
    lines.append(f"[bold]Kernel[/bold]   {si.kernel}")
    lines.append(f"[bold]Uptime[/bold]   {uptime}")

    # CPU
    freq_str = f" @ {cpu.frequency_current_mhz:.0f} MHz" if cpu.frequency_current_mhz else ""
    phys = f"{cpu.core_count_physical}P/" if cpu.core_count_physical else ""
    lines.append(
        f"[bold]CPU[/bold]      {phys}{cpu.core_count_logical} cores{freq_str}"
        f" — {_color_percent(cpu.percent_overall)}"
    )

    # Load average
    if cpu.load_avg_1 is not None:
        load_str = (
            f"[bold]Load[/bold]     {cpu.load_avg_1:.2f}  "
            f"{cpu.load_avg_5:.2f}  {cpu.load_avg_15:.2f}"
        )
        lines.append(load_str)

    # Memory
    lines.append(
        f"[bold]Memory[/bold]   {human_bytes(mem.used)} / {human_bytes(mem.total)}"
        f" — {_color_percent(mem.percent)}"
    )

    # Swap
    if mem.swap_total > 0:
        lines.append(
            f"[bold]Swap[/bold]     {human_bytes(mem.swap_used)} / {human_bytes(mem.swap_total)}"
            f" — {_color_percent(mem.swap_percent)}"
        )

    # Disk (first partition only for brevity)
    if disk.partitions:
        dp = disk.partitions[0]
        lines.append(
            f"[bold]Disk[/bold]     {human_bytes(dp.used)} / {human_bytes(dp.total)}"
            f" — {_color_percent(dp.percent)}  ({dp.mountpoint})"
        )

    # Network (first non-loopback interface with an address)
    for iface in net.interfaces:
        if iface.name.startswith("lo"):
            continue
        if iface.addrs:
            lines.append(f"[bold]Network[/bold]  {iface.name}  {iface.addrs[0]}")
            break

    # Temperatures
    if sensors.temperatures:
        temp_strs = [f"{t.label}: {t.current:.0f}°C" for t in sensors.temperatures[:4]]
        lines.append(f"[bold]Temps[/bold]    {', '.join(temp_strs)}")

    # Fans
    if sensors.fans:
        fan_strs = [f"{f.label}: {f.current} RPM" for f in sensors.fans[:3]]
        lines.append(f"[bold]Fans[/bold]     {', '.join(fan_strs)}")

    # Battery
    if sensors.battery:
        plugged = "⚡ plugged" if sensors.battery.power_plugged else "🔋 battery"
        lines.append(f"[bold]Battery[/bold]  {sensors.battery.percent:.0f}% {plugged}")

    # Containers
    docker_count = sum(1 for c in containers.containers if c.runtime == "docker")
    lxc_count = sum(1 for c in containers.containers if c.runtime == "lxc")
    running = sum(1 for c in containers.containers if c.status in ("running", "up"))
    if docker_count or lxc_count:
        parts = []
        if docker_count:
            parts.append(f"Docker: {docker_count}")
        if lxc_count:
            parts.append(f"LXC: {lxc_count}")
        parts.append(f"{running} running")
        lines.append(f"[bold]Containers[/bold] {', '.join(parts)}")

    # Users
    if snap.users:
        user_names = list({u.name for u in snap.users})
        lines.append(f"[bold]Users[/bold]    {', '.join(user_names)}")

    # Processes count
    lines.append(f"[bold]Procs[/bold]    {len(snap.processes)}")

    # ── Assemble side-by-side layout ─────────────────────────────────
    art_lines = _RAVEN_ART.strip().splitlines()
    info_lines = lines

    # Pad to equal height
    max_height = max(len(art_lines), len(info_lines))
    while len(art_lines) < max_height:
        art_lines.append("")
    while len(info_lines) < max_height:
        info_lines.append("")

    art_width = max(len(line) for line in art_lines) + 4

    combined: list[str] = []
    for art, info in zip(art_lines, info_lines, strict=False):
        padded_art = art.ljust(art_width)
        combined.append(f"[bold magenta]{padded_art}[/bold magenta]{info}")

    output = "\n".join(combined)
    console.print()
    console.print(
        Panel(
            output,
            title="[bold bright_white]🐦‍⬛ RAVEN[/bold bright_white]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()
