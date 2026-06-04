"""Process table widget — sortable DataTable of running processes."""

from __future__ import annotations

from textual.widgets import DataTable

from raven.core.models import ProcessInfo, SystemSnapshot


def _human_bytes(n: int | float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.0f}TB"


class ProcessTable(DataTable):
    """Process list as a sortable data table."""

    _sort_key: str = "cpu_percent"
    _sort_reverse: bool = True

    def on_mount(self) -> None:
        self.add_columns("PID", "Name", "User", "CPU%", "MEM%", "RSS", "Threads", "Status")
        self.cursor_type = "row"
        self.zebra_stripes = True

    def update_data(self, snap: SystemSnapshot, max_display: int = 25, sort_by: str = "cpu") -> None:
        # Determine sort
        sort_map = {
            "cpu": ("cpu_percent", True),
            "memory": ("memory_percent", True),
            "pid": ("pid", False),
            "name": ("name", False),
        }
        key, rev = sort_map.get(sort_by, ("cpu_percent", True))

        procs = sorted(snap.processes, key=lambda p: getattr(p, key, 0), reverse=rev)
        procs = procs[:max_display]

        self.clear()
        for p in procs:
            # Color-code CPU
            cpu_str = f"{p.cpu_percent:.1f}"
            mem_str = f"{p.memory_percent:.1f}"
            self.add_row(
                str(p.pid),
                p.name[:25],
                p.username[:12] if p.username else "—",
                cpu_str,
                mem_str,
                _human_bytes(p.memory_rss),
                str(p.num_threads),
                p.status[:8],
            )
