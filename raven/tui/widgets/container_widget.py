"""Container widget — Docker/LXC container list."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from raven.core.models import SystemSnapshot


class ContainerWidget(Static):
    """Container panel showing Docker and LXC containers."""

    def update_data(self, snap: SystemSnapshot) -> None:
        containers = snap.containers
        text = Text()
        text.append("  Containers\n", style="bold cyan")

        if not containers.containers:
            runtimes = []
            if not containers.docker_available:
                runtimes.append("Docker")
            if not containers.lxc_available:
                runtimes.append("LXC")
            text.append(f"  No containers ({', '.join(runtimes)} not found)\n", style="dim")
            self.update(text)
            return

        running = sum(1 for c in containers.containers if c.status in ("running", "up"))
        text.append(f"  {running}/{len(containers.containers)} running\n\n", style="")

        for c in containers.containers[:8]:
            status_color = "green" if c.status in ("running", "up") else "yellow"
            text.append(f"  [{c.runtime}] ", style="dim")
            text.append(f"{c.name[:20]:<22}", style="bold")
            text.append(f"{c.status:<12}", style=status_color)
            text.append(f"{c.image[:25]}\n", style="dim")

        self.update(text)
