"""Container monitoring plugin (Docker + LXC)."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

from raven.core.models import ContainerInfo, ContainerMetrics
from raven.plugins.base import MonitorPlugin


class ContainersPlugin(MonitorPlugin):
    name = "containers"
    category = "containers"

    def is_available(self) -> bool:
        return self._docker_available() or self._lxc_available()

    def collect(self) -> ContainerMetrics:
        docker_ok = self._docker_available()
        lxc_ok = self._lxc_available()

        containers: list[ContainerInfo] = []

        if docker_ok:
            containers.extend(self._collect_docker())
        if lxc_ok:
            containers.extend(self._collect_lxc())

        return ContainerMetrics(
            containers=containers,
            docker_available=docker_ok,
            lxc_available=lxc_ok,
        )

    # ── Docker ───────────────────────────────────────────────────────────

    @staticmethod
    def _docker_available() -> bool:
        try:
            import docker  # noqa: F401
            client = docker.from_env()
            client.ping()
            return True
        except Exception:
            return False

    @staticmethod
    def _collect_docker() -> list[ContainerInfo]:
        containers: list[ContainerInfo] = []
        try:
            import docker

            client = docker.from_env()
            for c in client.containers.list(all=True):
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
            pass
        return containers

    # ── LXC ──────────────────────────────────────────────────────────────

    @staticmethod
    def _lxc_available() -> bool:
        return shutil.which("lxc") is not None

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

            data: list[dict[str, Any]] = json.loads(result.stdout)
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
            pass
        return containers


PLUGIN_INFO = {
    "name": "containers",
    "category": "containers",
    "class": ContainersPlugin,
}
