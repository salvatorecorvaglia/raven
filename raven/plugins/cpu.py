"""CPU monitoring plugin."""

from __future__ import annotations

import os

import psutil

from raven.core.models import CpuMetrics
from raven.plugins.base import MonitorPlugin

# Prime psutil's internal cpu_percent counter so that the first real
# ``collect()`` call returns a meaningful value instead of 0.0.
psutil.cpu_percent(interval=None)


class CpuPlugin(MonitorPlugin):
    name = "cpu"
    category = "cpu"

    def is_available(self) -> bool:
        return True

    def collect(self) -> CpuMetrics:
        freq = psutil.cpu_freq()
        # Load average is not available on Windows
        try:
            load1, load5, load15 = os.getloadavg()
        except (OSError, AttributeError):
            load1 = load5 = load15 = None

        cpu_stats = psutil.cpu_stats()

        return CpuMetrics(
            percent_overall=psutil.cpu_percent(interval=0),
            percent_per_core=psutil.cpu_percent(interval=0, percpu=True),
            core_count_logical=psutil.cpu_count(logical=True) or 0,
            core_count_physical=psutil.cpu_count(logical=False),
            frequency_current_mhz=freq.current if freq else None,
            frequency_max_mhz=freq.max if freq else None,
            load_avg_1=load1,
            load_avg_5=load5,
            load_avg_15=load15,
            ctx_switches=cpu_stats.ctx_switches,
            interrupts=cpu_stats.interrupts,
        )


PLUGIN_INFO = {
    "name": "cpu",
    "category": "cpu",
    "class": CpuPlugin,
}
