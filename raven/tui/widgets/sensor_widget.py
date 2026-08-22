"""Sensor widget — temperatures, fans, battery, users."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from raven.core.models import SystemSnapshot
from raven.core.utils import color_for_temp
from raven.tui.widgets._common import section_header


class SensorWidget(Static):
    """Sensors panel — temperatures, fans, battery, users."""

    def update_data(self, snap: SystemSnapshot) -> None:
        sensors = snap.sensors
        text = Text()

        # Temperatures
        if sensors.temperatures:
            section_header(text, "Temps")
            for t in sensors.temperatures[:6]:
                color = color_for_temp(t.current, t.high, t.critical)
                text.append(f"  {t.label:<18} ", style="")
                text.append(f"{t.current:.0f}°C", style=color)
                if t.high:
                    text.append(f" (high: {t.high:.0f}°C)", style="dim")
                text.append("\n")

        # Fans
        if sensors.fans:
            section_header(text, "Fans")
            for f in sensors.fans[:4]:
                text.append(f"  {f.label:<18} {f.current} RPM\n")

        # Battery
        if sensors.battery:
            bat = sensors.battery
            section_header(text, "Battery")
            plugged = "⚡ Plugged" if bat.power_plugged else "🔋 Battery"
            color = "green" if (bat.percent or 0) > 20 else "red"
            pct_str = f"{bat.percent:.0f}%" if bat.percent is not None else "Unknown"
            text.append(f"  {pct_str} {plugged}\n", style=color)

        # Users
        if snap.users:
            user_names = list({u.name for u in snap.users})[:5]
            section_header(text, "Users")
            text.append(f"  {', '.join(user_names)}\n", style="")

        if not text.plain.strip():
            text.append("  No sensor data\n", style="dim")

        self.update(text)
