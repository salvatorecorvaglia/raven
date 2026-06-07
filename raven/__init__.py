"""Raven — Cross-platform system monitor."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("raven-monitor")
except PackageNotFoundError:
    __version__ = "0.1.0"  # fallback for editable installs without metadata

__app_name__ = "raven"
