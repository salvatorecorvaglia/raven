"""Container monitoring plugin (Docker + LXC)."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
from typing import Any

from raven.core.models import ContainerInfo, ContainerMetrics
from raven.plugins.base import MonitorPlugin

log = logging.getLogger(__name__)

# Maximum stdout size from LXC commands (10 MB) to prevent OOM
_LXC_MAX_OUTPUT = 10 * 1024 * 1024


class ContainersPlugin(MonitorPlugin):
    name = "containers"
    category = "containers"

    def __init__(self) -> None:
        super().__init__()
        # Cache Docker/LXC availability to avoid repeated expensive checks
        self._docker_ok: bool | None = None
        self._lxc_ok: bool | None = None
        self._last_check: float = 0
        self._cache_ttl: float = 30.0  # re-check every 30 seconds
        self._docker_client: Any = None

    def is_available(self) -> bool:
        self._refresh_availability()
        return bool(self._docker_ok or self._lxc_ok)

    def collect(self) -> ContainerMetrics:
        self._refresh_availability()

        containers: list[ContainerInfo] = []

        if self._docker_ok:
            containers.extend(self._collect_docker())
        if self._lxc_ok:
            containers.extend(self._collect_lxc())

        return ContainerMetrics(
            containers=containers,
            docker_available=bool(self._docker_ok),
            lxc_available=bool(self._lxc_ok),
        )

    # ── Availability caching ─────────────────────────────────────────

    def _refresh_availability(self) -> None:
        """Re-check Docker/LXC availability if the cache has expired."""
        now = time.monotonic()
        if self._docker_ok is not None and (now - self._last_check) < self._cache_ttl:
            return

        self._docker_ok = self._check_docker()
        self._lxc_ok = shutil.which("lxc") is not None
        self._last_check = now

    def _check_docker(self) -> bool:
        try:
            import docker  # noqa: F401
            if self._docker_client is None:
                self._docker_client = docker.from_env()
            self._docker_client.ping()
            return True
        except Exception:
            self._docker_client = None
            return False

    # ── Docker ───────────────────────────────────────────────────────────

    def _collect_docker(self) -> list[ContainerInfo]:
        containers: list[ContainerInfo] = []
        try:
            if self._docker_client is None:
                import docker
                self._docker_client = docker.from_env()

            for c in self._docker_client.containers.list(all=True):
                containers.append(
                    ContainerInfo(
                        name=c.name or "",
                        container_id=c.short_id,
                        image=str(c.image.tags[0]) if c.image.tags else str(c.image.id[:12]),
                        status=c.status,
                        runtime="docker",
                    )
                )
        except Exception:
            log.debug("Docker collection failed", exc_info=True)
        return containers

    # ── LXC ──────────────────────────────────────────────────────────────

    @staticmethod
    def _collect_lxc() -> list[ContainerInfo]:
        containers: list[ContainerInfo] = []
        try:
            result = subprocess.run(
                ["lxc", "list", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return containers

            # SEC-4: Guard against oversized output
            stdout = result.stdout
            if len(stdout) > _LXC_MAX_OUTPUT:
                log.warning("LXC output exceeded %d bytes, truncating", _LXC_MAX_OUTPUT)
                return containers

            data: list[dict[str, Any]] = json.loads(stdout)
            for entry in data:
                containers.append(
                    ContainerInfo(
                        name=entry.get("name", ""),
                        container_id=entry.get("name", ""),
                        image=entry.get("config", {}).get("image.description", ""),
                        status=entry.get("status", "").lower(),
                        runtime="lxc",
                    )
                )
        except Exception:
            log.debug("LXC collection failed", exc_info=True)
        return containers


PLUGIN_INFO = {
    "name": "containers",
    "category": "containers",
    "class": ContainersPlugin,
}
