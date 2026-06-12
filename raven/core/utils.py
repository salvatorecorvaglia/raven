"""Shared utility helpers for Raven.

Centralised here to avoid duplication across plugins, widgets, and exporters.
"""

from __future__ import annotations

import rich.text


def human_bytes(n: int | float) -> str:
    """Convert bytes to a human-readable string (e.g. ``1.5 GB``)."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def human_bytes_compact(n: int | float) -> str:
    """Compact variant without decimal for small values (used in process tables)."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.0f}{unit}" if n >= 1 else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.0f}PB"


def color_for_percent(pct: float, thresholds: tuple[float, float] = (50.0, 80.0)) -> str:
    """Return a colour name for a percentage value.

    Parameters
    ----------
    pct:
        The percentage (0–100).
    thresholds:
        ``(warn, crit)`` — below *warn* is green, below *crit* is yellow,
        above is red.
    """
    warn, crit = thresholds
    if pct < warn:
        return "green"
    elif pct < crit:
        return "yellow"
    return "red"


def text_sparkline(history) -> str:
    """Render a text-based sparkline from a sequence of floats.

    Returns a string of Unicode block characters.
    """
    if len(history) < 2:
        return ""
    spark_chars = " ▂▃▄▅▆▇█"
    max_val = max(history) or 1
    spark = ""
    for v in history:
        idx = int(v / max_val * (len(spark_chars) - 1))
        idx = max(0, min(idx, len(spark_chars) - 1))
        spark += spark_chars[idx]
    return spark


def render_bar(
    pct: float,
    width: int = 20,
    style_color: str | None = None,
    bracketed: bool = False,
) -> rich.text.Text:
    """Render a progress bar using Rich Text.

    Parameters
    ----------
    pct:
        The percentage (0-100).
    width:
        The character width of the filled/unfilled portion of the bar.
    style_color:
        Explicit colour name, or None to determine based on percentage thresholds.
    bracketed:
        If True, wraps the bar with dim brackets '[ ]'.
    """
    filled = int(width * pct / 100)
    filled = max(0, min(filled, width))
    color = style_color or color_for_percent(pct)
    t = rich.text.Text()
    if bracketed:
        t.append("[", style="dim")
    t.append("█" * filled, style=color)
    t.append("░" * (width - filled), style="dim")
    if bracketed:
        t.append("]", style="dim")
    t.append(f" {pct:5.1f}%", style=f"bold {color}")
    return t
