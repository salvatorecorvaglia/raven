"""CSV export formatter."""

from __future__ import annotations

import csv
import io
from dataclasses import asdict

from raven.core.models import SystemSnapshot
from raven.export.base import BaseExporter


def _flatten(data: dict, prefix: str = "") -> dict[str, str]:
    """Flatten a nested dict into dot-separated keys."""
    items: dict[str, str] = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            items.update(_flatten(value, full_key))
        elif isinstance(value, list):
            if len(value) == 0:
                items[full_key] = ""
            elif isinstance(value[0], dict):
                for i, item in enumerate(value[:50]):  # cap to 50 items
                    items.update(_flatten(item, f"{full_key}[{i}]"))
            else:
                items[full_key] = "; ".join(str(v) for v in value)
        else:
            items[full_key] = str(value) if value is not None else ""
    return items


class CsvExporter(BaseExporter):
    name = "csv"

    def format(self, snapshot: SystemSnapshot, modules: list[str] | None = None) -> str:
        data = asdict(snapshot)
        if modules:
            filtered = {"timestamp": data["timestamp"]}
            for mod in modules:
                if mod in data:
                    filtered[mod] = data[mod]
            data = filtered

        flat = _flatten(data)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(flat.keys())
        writer.writerow(flat.values())
        return buf.getvalue()
