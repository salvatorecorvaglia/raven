"""Sensor widget — temperatures, fans, battery."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from raven.core.models import SystemSnapshot


def _temp_color(temp: float, high: float | None = None, crit: float | None = None) -> str:
    if crit and temp >= crit:
        return "red bold"
    if high and temp >= high:
        return "yellow"
    if temp >= 80:
        return "yellow"
    return "green"


class SensorWidget(Static):
    """Sensors panel — temperatures, fans, battery."""

    def update_data(self, snap: SystemSnapshot) -> None:
        sensors = snap.sensors
        text = Text()

        # Temperatures
        if sensors.temperatures:
            text.append("  Temps\n", style="bold cyan")
            for t in sensors.temperatures[:6]:
                color = _temp_color(t.current, t.high, t.critical)
                text.append(f"  {t.label:<18} ", style="")
                text.append(f"{t.current:.0f}°C", style=color)
                if t.high:
                    text.append(f" (high: {t.high:.0f}°C)", style="dim")
                text.append("\n")

        # Fans
        if sensors.fans:
            text.append("  Fans\n", style="bold cyan")
            for f in sensors.fans[:4]:
                text.append(f"  {f.label:<18} {f.current} RPM\n")

        # Battery
        if sensors.battery:
            bat = sensors.battery
            text.append("  Battery\n", style="bold cyan")
            plugged = "⚡ Plugged" if bat.power_plugged else "🔋 Battery"
            color = "green" if (bat.percent or 0) > 20 else "red"
            text.append(f"  {bat.percent:.0f}% {plugged}\n", style=color)

        # Users + Containers summary
        if snap.users:
            user_names = list({u.name for u in snap.users})[:5]
            text.append("  Users\n", style="bold cyan")
            text.append(f"  {', '.join(user_names)}\n", style="")

        if snap.containers.containers:
            running = sum(1 for c in snap.containers.containers if c.status in ("running", "up"))
            total = len(snap.containers.containers)
            text.append("  Containers\n", style="bold cyan")
            text.append(f"  {running}/{total} running\n", style="green" if running else "dim")
            for c in snap.containers.containers[:4]:
                status_color = "green" if c.status in ("running", "up") else "yellow"
                text.append(f"  {c.name[:16]:<18}", style="")
                text.append(f"{c.status}\n", style=status_color)

        if not text.plain.strip():
            text.append("  No sensor data\n", style="dim")

        self.update(text)
