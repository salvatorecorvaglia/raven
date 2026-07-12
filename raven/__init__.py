"""Raven — Cross-platform system monitor."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("raven-monitor")
except PackageNotFoundError:
    __version__ = "0.5.0"  # fallback for editable installs without metadata

__app_name__ = "raven"

__all__ = ["__version__", "__app_name__"]
