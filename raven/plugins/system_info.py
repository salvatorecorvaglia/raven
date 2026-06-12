"""System information plugin (hostname, OS, kernel, uptime, etc.)."""

from __future__ import annotations

import getpass
import platform
import time

import psutil

from raven.core.models import SystemInfoMetrics
from raven.plugins.base import MonitorPlugin


class SystemInfoPlugin(MonitorPlugin):
    name = "system_info"
    category = "system_info"

    def is_available(self) -> bool:
        return True

    def collect(self) -> SystemInfoMetrics:
        boot = psutil.boot_time()
        uptime = time.time() - boot

        # OS version string
        if platform.system() == "Darwin":
            os_version = platform.mac_ver()[0] or platform.version()
        elif platform.system() == "Windows":
            os_version = platform.version()
        else:
            os_version = platform.version()

        try:
            username = getpass.getuser()
        except Exception:
            username = ""

        return SystemInfoMetrics(
            hostname=platform.node(),
            os_name=platform.system(),
            os_version=os_version,
            os_release=platform.platform(),
            kernel=platform.release(),
            architecture=platform.machine(),
            uptime_seconds=uptime,
            boot_time=boot,
            python_version=platform.python_version(),
            username=username,
        )
