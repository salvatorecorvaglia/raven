"""Container widget — Docker/LXC container list."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from raven.core.models import SystemSnapshot
from raven.tui.widgets._common import section_header


class ContainerWidget(Static):
    """Container panel showing Docker and LXC containers."""

    def update_data(self, snap: SystemSnapshot) -> None:
        containers = snap.containers

        # Auto-hide if neither runtime is available
        if not containers.docker_available and not containers.lxc_available:
            self.display = False
            try:
                self.app.query_one("#dashboard").add_class("no-containers")
            except Exception:
                pass
            return
        else:
            self.display = True
            try:
                self.app.query_one("#dashboard").remove_class("no-containers")
            except Exception:
                pass

        text = Text()
        section_header(text, "Containers")

        if not containers.containers:
            text.append("  No containers detected\n", style="dim")
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
