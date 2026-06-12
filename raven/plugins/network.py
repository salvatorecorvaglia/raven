"""Network monitoring plugin."""

from __future__ import annotations

import psutil

from raven.core.models import NetworkInterface, NetworkMetrics
from raven.plugins.base import MonitorPlugin


class NetworkPlugin(MonitorPlugin):
    name = "network"
    category = "network"

    def is_available(self) -> bool:
        return True

    def collect(self) -> NetworkMetrics:
        counters = psutil.net_io_counters(pernic=True)
        addrs = psutil.net_if_addrs()

        interfaces: list[NetworkInterface] = []
        for iface_name, stats in counters.items():
            # Collect addresses for this interface
            iface_addrs: list[str] = []
            if iface_name in addrs:
                for addr in addrs[iface_name]:
                    if addr.family.name in ("AF_INET", "AF_INET6"):
                        iface_addrs.append(addr.address)

            interfaces.append(
                NetworkInterface(
                    name=iface_name,
                    bytes_sent=stats.bytes_sent,
                    bytes_recv=stats.bytes_recv,
                    packets_sent=stats.packets_sent,
                    packets_recv=stats.packets_recv,
                    addrs=iface_addrs,
                )
            )

        # Connection count
        try:
            conn_count = len(psutil.net_connections(kind="inet"))
        except (psutil.AccessDenied, OSError):
            conn_count = 0

        return NetworkMetrics(
            interfaces=interfaces,
            connections_count=conn_count,
        )
