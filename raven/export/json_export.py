"""JSON export formatter."""

from __future__ import annotations

import json
from dataclasses import asdict

from raven.core.models import SystemSnapshot
from raven.export.base import BaseExporter


class JsonExporter(BaseExporter):
    name = "json"

    def format(self, snapshot: SystemSnapshot, modules: list[str] | None = None) -> str:
        data = asdict(snapshot)
        if modules:
            filtered = {"timestamp": data["timestamp"]}
            for mod in modules:
                if mod in data:
                    filtered[mod] = data[mod]
            data = filtered
        return json.dumps(data, indent=2, default=str)
