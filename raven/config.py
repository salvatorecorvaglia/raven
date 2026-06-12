"""TOML-based configuration for Raven.

Search order (first match wins):
1. ``--config`` CLI flag
2. ``./raven.toml``
3. ``~/.config/raven/raven.toml``
4. Built-in defaults
"""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


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
        "host": "127.0.0.1",
        "port": 8080,
        "api_key": "",
    },
    "remote": {
        "enabled": False,
        "host": "127.0.0.1",
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
    host: str = "127.0.0.1"
    port: int = 8080
    api_key: str = ""


@dataclass
class RemoteConfig:
    enabled: bool = False
    host: str = "127.0.0.1"
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
    """Locate the first existing config file in search order.

    Raises
    ------
    FileNotFoundError
        If *explicit_path* is given but does not point to an existing file.
    """
    if explicit_path:
        p = Path(explicit_path)
        if not p.is_file():
            raise FileNotFoundError(
                f"Config file not found: {explicit_path!r}"
            )
        return p

    candidates = [
        Path.cwd() / "raven.toml",
        Path.home() / ".config" / "raven" / "raven.toml",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _dict_to_config(data: dict[str, Any]) -> RavenConfig:
    """Convert a merged dict to a ``RavenConfig`` instance.

    Unknown keys in each section are filtered out with a warning.
    """
    section_classes: dict[str, type] = {
        "general": GeneralConfig,
        "modules": ModulesConfig,
        "web": WebConfig,
        "remote": RemoteConfig,
        "export": ExportConfig,
        "processes": ProcessesConfig,
    }

    sections: dict[str, Any] = {}
    for section_name, cls in section_classes.items():
        raw = data.get(section_name, {})
        valid_keys = {f.name for f in fields(cls)}
        filtered: dict[str, Any] = {}
        for k, v in raw.items():
            if k in valid_keys:
                filtered[k] = v
            else:
                log.warning(
                    "Unknown config key '%s' in [%s] — ignoring",
                    k,
                    section_name,
                )
        sections[section_name] = cls(**filtered)

    return RavenConfig(
        general=sections["general"],
        modules=sections["modules"],
        web=sections["web"],
        remote=sections["remote"],
        export=sections["export"],
        processes=sections["processes"],
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
