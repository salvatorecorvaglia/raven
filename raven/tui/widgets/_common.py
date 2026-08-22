"""Small helpers shared across dashboard widgets."""

from __future__ import annotations

from rich.text import Text


def section_header(text: Text, title: str) -> None:
    """Append a widget's bold-cyan section header line (e.g. "  CPU\\n")."""
    text.append(f"  {title}\n", style="bold cyan")
