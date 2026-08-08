"""CPU monitoring plugin."""

from __future__ import annotations

import os

import psutil

from raven.core.models import CpuMetrics
from raven.plugins.base import MonitorPlugin

# Prime psutil's internal cpu_percent counter so that the first real
# ``collect()`` call returns a meaningful value instead of 0.0.
psutil.cpu_percent(interval=None)
psutil.cpu_percent(interval=None, percpu=True)


class CpuPlugin(MonitorPlugin):
    name = "cpu"
    category = "cpu"

    def is_available(self) -> bool:
        return True

    @staticmethod
    def _normalise_mhz(value: float | None) -> float | None:
        """Return a frequency in MHz.

        psutil reports GHz rather than MHz on some platforms (notably macOS on
        Apple Silicon, where ``cpu_freq()`` returns ``current=4``), which would
        otherwise be rendered as "4 MHz". No real CPU runs below 10 MHz, so a
        value that small is unambiguously GHz.
        """
        if value is None or value <= 0:
            return None
        return value * 1000 if value < 10 else value

    def collect(self) -> CpuMetrics:
        freq = None
        if hasattr(psutil, "cpu_freq"):
            try:
                freq = psutil.cpu_freq()
            except Exception:
                pass
        # Load average is not available on Windows
        load1: float | None
        load5: float | None
        load15: float | None
        try:
            load1, load5, load15 = os.getloadavg()
        except (OSError, AttributeError):
            load1 = load5 = load15 = None

        cpu_stats = psutil.cpu_stats()

        percent_per_core = psutil.cpu_percent(interval=0, percpu=True)
        percent_overall = sum(percent_per_core) / len(percent_per_core) if percent_per_core else 0.0
        percent_overall = round(percent_overall, 1)

        return CpuMetrics(
            percent_overall=percent_overall,
            percent_per_core=percent_per_core,
            core_count_logical=psutil.cpu_count(logical=True) or 0,
            core_count_physical=psutil.cpu_count(logical=False),
            frequency_current_mhz=self._normalise_mhz(freq.current) if freq else None,
            frequency_max_mhz=self._normalise_mhz(freq.max) if freq else None,
            load_avg_1=load1,
            load_avg_5=load5,
            load_avg_15=load15,
            ctx_switches=cpu_stats.ctx_switches,
            interrupts=cpu_stats.interrupts,
        )
