"""Plugin discovery and loading.

Discovers built-in plugins from the ``raven.plugins`` package and
instantiates those enabled in the configuration.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any

from raven.config import RavenConfig
from raven.plugins.base import MonitorPlugin

log = logging.getLogger(__name__)

# Built-in plugin module names (relative to raven.plugins)
_BUILTIN_PLUGINS = [
    "cpu",
    "memory",
    "disk",
    "network",
    "processes",
    "users",
    "sensors",
    "containers",
    "system_info",
]

# Map plugin names → module config field names
_NAME_TO_CONFIG = {
    "cpu": "cpu",
    "memory": "memory",
    "disk": "disk",
    "network": "network",
    "processes": "processes",
    "users": "users",
    "sensors": "sensors",
    "containers": "containers",
    "system_info": None,  # always enabled — lightweight
}


def _load_plugin_module(module_name: str) -> type[MonitorPlugin] | None:
    """Import a plugin module and return its ``MonitorPlugin`` class."""
    fqn = f"raven.plugins.{module_name}"
    try:
        mod = importlib.import_module(fqn)
        for name in dir(mod):
            obj = getattr(mod, name)
            if (
                isinstance(obj, type)
                and issubclass(obj, MonitorPlugin)
                and obj is not MonitorPlugin
            ):
                return obj
        log.warning("Plugin module %s has no MonitorPlugin subclass — skipping", fqn)
        return None
    except Exception:
        log.exception("Failed to load plugin module %s", fqn)
        return None


def get_enabled_plugins(config: RavenConfig) -> list[MonitorPlugin]:
    """Return instantiated plugin objects for all enabled modules."""
    plugins: list[MonitorPlugin] = []

    for mod_name in _BUILTIN_PLUGINS:
        # Check if the module is enabled in config
        config_key = _NAME_TO_CONFIG.get(mod_name)
        if config_key is not None:
            if not getattr(config.modules, config_key, True):
                log.debug("Plugin %s disabled by config", mod_name)
                continue

        cls = _load_plugin_module(mod_name)
        if cls is None:
            continue

        # Try to pass the configuration if the plugin constructor supports it
        try:
            instance: MonitorPlugin = cls(config=config)
        except TypeError:
            instance: MonitorPlugin = cls()

        if instance.is_available():
            plugins.append(instance)
            log.debug("Loaded plugin: %s", instance.name)
        else:
            log.debug("Plugin %s not available on this platform", instance.name)

    return plugins
