"""TOML-based configuration for Raven.

Search order (first match wins):
1. ``--config`` CLI flag
2. ``./raven.toml``
3. ``~/.config/raven/raven.toml``
4. Built-in defaults
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Defaults ─────────────────────────────────────────────────────────────────

_DEFAULTS: dict[str, Any] = {
    "general": {
        "refresh_interval": 2,
        "theme": "dark",
    },
    "modules": {
        "cpu": True,
        "memory": True,
        "disk": True,
        "network": True,
        "processes": True,
        "users": True,
        "sensors": True,
        "containers": True,
    },
    "web": {
        "enabled": False,
        "host": "0.0.0.0",
        "port": 8080,
        "api_key": "",
    },
    "remote": {
        "enabled": False,
        "host": "0.0.0.0",
        "port": 9090,
        "api_key": "",
    },
    "export": {
        "format": "text",
    },
    "processes": {
        "max_display": 25,
        "sort_by": "cpu",
    },
}


# ── Config Dataclass ─────────────────────────────────────────────────────────

@dataclass
class GeneralConfig:
    refresh_interval: int = 2
    theme: str = "dark"


@dataclass
class ModulesConfig:
    cpu: bool = True
    memory: bool = True
    disk: bool = True
    network: bool = True
    processes: bool = True
    users: bool = True
    sensors: bool = True
    containers: bool = True


@dataclass
class WebConfig:
    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 8080
    api_key: str = ""


@dataclass
class RemoteConfig:
    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 9090
    api_key: str = ""


@dataclass
class ExportConfig:
    format: str = "text"


@dataclass
class ProcessesConfig:
    max_display: int = 25
    sort_by: str = "cpu"


@dataclass
class RavenConfig:
    general: GeneralConfig = field(default_factory=GeneralConfig)
    modules: ModulesConfig = field(default_factory=ModulesConfig)
    web: WebConfig = field(default_factory=WebConfig)
    remote: RemoteConfig = field(default_factory=RemoteConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    processes: ProcessesConfig = field(default_factory=ProcessesConfig)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base* (non-destructive)."""
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _find_config_file(explicit_path: str | None = None) -> Path | None:
    """Locate the first existing config file in search order."""
    if explicit_path:
        p = Path(explicit_path)
        return p if p.is_file() else None

    candidates = [
        Path.cwd() / "raven.toml",
        Path.home() / ".config" / "raven" / "raven.toml",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _dict_to_config(data: dict[str, Any]) -> RavenConfig:
    """Convert a merged dict to a ``RavenConfig`` instance."""
    return RavenConfig(
        general=GeneralConfig(**data.get("general", {})),
        modules=ModulesConfig(**data.get("modules", {})),
        web=WebConfig(**data.get("web", {})),
        remote=RemoteConfig(**data.get("remote", {})),
        export=ExportConfig(**data.get("export", {})),
        processes=ProcessesConfig(**data.get("processes", {})),
    )


# ── Public API ───────────────────────────────────────────────────────────────

def load_config(explicit_path: str | None = None) -> RavenConfig:
    """Load and merge configuration, returning a ``RavenConfig``.

    Parameters
    ----------
    explicit_path:
        Optional path to a TOML config file.  Overrides auto-discovery.
    """
    config_file = _find_config_file(explicit_path)
    if config_file is not None:
        with open(config_file, "rb") as fh:
            user_data = tomllib.load(fh)
    else:
        user_data = {}

    merged = _deep_merge(_DEFAULTS, user_data)
    return _dict_to_config(merged)
