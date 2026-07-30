"""Shared utility helpers for Raven.

Centralised here to avoid duplication across plugins, widgets, and exporters.
"""

from __future__ import annotations

from typing import Any

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


def color_for_percent(pct: float | None, thresholds: tuple[float, float] = (50.0, 80.0)) -> str:
    """Return a colour name or hex string for a percentage value.

    Parameters
    ----------
    pct:
        The percentage (0–100) or None.
    thresholds:
        ``(warn, crit)`` — below *warn* is cyan, below *crit* is amber,
        above is red/coral.
    """
    if pct is None:
        pct = 0.0
    warn, crit = thresholds
    if pct < warn:
        return "#00d2ff"
    elif pct < crit:
        return "#f59e0b"
    return "#ef4444"


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
        val = v if v is not None else 0.0
        idx = int(val / max_val * (len(spark_chars) - 1))
        idx = max(0, min(idx, len(spark_chars) - 1))
        spark += spark_chars[idx]
    return spark


def render_bar(
    pct: float | None,
    width: int = 20,
    style_color: str | None = None,
    bracketed: bool = False,
    filled_char: str = "━",
    unfilled_char: str = "─",
) -> rich.text.Text:
    """Render a sleek progress bar using Rich Text.

    Parameters
    ----------
    pct:
        The percentage (0-100) or None.
    width:
        The character width of the filled/unfilled portion of the bar.
    style_color:
        Explicit colour name, or None to determine based on percentage thresholds.
    bracketed:
        If True, wraps the bar with dim brackets '[ ]'.
    filled_char:
        Character used for filled portion (default '━').
    unfilled_char:
        Character used for empty portion (default '─').
    """
    safe_pct = 0.0 if pct is None else pct
    filled = int(width * safe_pct / 100)
    filled = max(0, min(filled, width))
    color = style_color or color_for_percent(safe_pct)
    t = rich.text.Text()
    if bracketed:
        t.append("[", style="dim")
    t.append(filled_char * filled, style=color)
    t.append(unfilled_char * (width - filled), style="dim")
    if bracketed:
        t.append("]", style="dim")
    t.append(f" {safe_pct:5.1f}%", style=f"bold {color}")
    return t


def serialize_model(obj: Any) -> Any:
    """Recursively convert Raven models to dict/list structures.

    Bypasses slow dataclasses.asdict.
    """
    if hasattr(obj, "__dataclass_fields__"):
        return {f: serialize_model(getattr(obj, f)) for f in obj.__dataclass_fields__}
    elif isinstance(obj, list):
        return [serialize_model(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: serialize_model(v) for k, v in obj.items()}
    else:
        return obj
