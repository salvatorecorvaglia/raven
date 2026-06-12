"""Remote client — fetches metrics from a remote Raven agent.

Implements the same ``collect()`` / ``collect_async()`` interface as the
local ``Collector``, so TUI and exporters can seamlessly switch between
local and remote data sources.

Usage::

    raven --remote 10.0.0.5:9090
"""

from __future__ import annotations

import httpx

from raven.core.models import (
    BatteryInfo,
    ContainerInfo,
    ContainerMetrics,
    CpuMetrics,
    DiskIO,
    DiskMetrics,
    DiskPartition,
    FanReading,
    MemoryMetrics,
    NetworkInterface,
    NetworkMetrics,
    ProcessInfo,
    SensorMetrics,
    SystemInfoMetrics,
    SystemSnapshot,
    TemperatureReading,
    UserInfo,
)


class RemoteCollector:
    """Collects system metrics from a remote Raven agent via HTTP."""

    def __init__(self, address: str, api_key: str = "") -> None:
        # Normalise address
        if not address.startswith("http"):
            address = f"http://{address}"
        self.base_url = address.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        hdrs: dict[str, str] = {}
        if self.api_key:
            hdrs["X-API-Key"] = self.api_key
        return hdrs

    def collect(self) -> SystemSnapshot:
        """Synchronous fetch of a remote snapshot."""
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{self.base_url}/api/v1/snapshot",
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
        return self._parse(data)

    async def collect_async(self) -> SystemSnapshot:
        """Async fetch of a remote snapshot."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/snapshot",
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
        return self._parse(data)

    # ── Parsing ──────────────────────────────────────────────────────

    @staticmethod
    def _build(cls: type, data: dict | None):
        if not data:
            return cls()
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @staticmethod
    def _parse(data: dict) -> SystemSnapshot:
        """Convert a JSON dict back into a ``SystemSnapshot``."""
        cpu_data = data.get("cpu")
        mem_data = data.get("memory")
        disk_data = data.get("disk") or {}
        net_data = data.get("network") or {}
        si_data = data.get("system_info")
        sensor_data = data.get("sensors") or {}
        ct_data = data.get("containers") or {}

        # CPU
        cpu = RemoteCollector._build(CpuMetrics, cpu_data)

        # Memory
        mem = RemoteCollector._build(MemoryMetrics, mem_data)

        # Disk
        parts = [
            RemoteCollector._build(DiskPartition, p) for p in (disk_data.get("partitions") or [])
        ]
        disk_io = RemoteCollector._build(DiskIO, disk_data.get("io"))
        disk = DiskMetrics(partitions=parts, io=disk_io)

        # Network
        ifaces = [
            RemoteCollector._build(NetworkInterface, i) for i in (net_data.get("interfaces") or [])
        ]
        network = NetworkMetrics(
            interfaces=ifaces,
            connections_count=net_data.get("connections_count") or 0,
        )

        # Processes
        procs = [RemoteCollector._build(ProcessInfo, p) for p in (data.get("processes") or [])]

        # Users
        users = [RemoteCollector._build(UserInfo, u) for u in (data.get("users") or [])]

        # Sensors
        temps = [
            RemoteCollector._build(TemperatureReading, t)
            for t in (sensor_data.get("temperatures") or [])
        ]
        fans = [RemoteCollector._build(FanReading, f) for f in (sensor_data.get("fans") or [])]
        bat_raw = sensor_data.get("battery")
        battery = RemoteCollector._build(BatteryInfo, bat_raw) if bat_raw else None
        sensors = SensorMetrics(temperatures=temps, fans=fans, battery=battery)

        # Containers
        containers_list = [
            RemoteCollector._build(ContainerInfo, c) for c in (ct_data.get("containers") or [])
        ]
        containers = ContainerMetrics(
            containers=containers_list,
            docker_available=bool(ct_data.get("docker_available")),
            lxc_available=bool(ct_data.get("lxc_available")),
        )

        # System info
        sys_info = RemoteCollector._build(SystemInfoMetrics, si_data)

        return SystemSnapshot(
            timestamp=data.get("timestamp", 0.0),
            cpu=cpu,
            memory=mem,
            disk=disk,
            network=network,
            processes=procs,
            users=users,
            sensors=sensors,
            containers=containers,
            system_info=sys_info,
        )
