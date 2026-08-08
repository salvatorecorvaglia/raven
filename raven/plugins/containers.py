"""Container monitoring plugin (Docker + LXC)."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from typing import Any

from raven.core.models import ContainerInfo, ContainerMetrics
from raven.plugins.base import MonitorPlugin

log = logging.getLogger(__name__)

# Maximum stdout size from LXC commands (10 MB) to prevent OOM
_LXC_MAX_OUTPUT = 10 * 1024 * 1024

# Overall budget for gathering per-container stats, kept well under the
# collector's 10 s per-plugin future timeout.
_STATS_DEADLINE = 6.0


class ContainersPlugin(MonitorPlugin):
    name = "containers"
    category = "containers"

    def __init__(self, config=None) -> None:
        super().__init__(config)
        self._stats_enabled = bool(
            getattr(getattr(config, "modules", None), "container_stats", False)
        )
        # Cache Docker/LXC availability to avoid repeated expensive checks
        self._docker_ok: bool | None = None
        self._lxc_ok: bool | None = None
        self._last_check: float = 0
        self._cache_ttl: float = 30.0  # re-check every 30 seconds
        self._docker_client: Any = None
        self._lock = threading.RLock()

    def is_available(self) -> bool:
        """Always available when the module is enabled.

        Runtime presence of Docker/LXC is deliberately *not* decided here:
        ``get_enabled_plugins`` calls this once at startup, so gating on it
        would drop the plugin permanently if the Docker daemon happened to be
        down at launch. Presence is re-checked on every ``collect()`` (behind
        a 30 s cache) and reported via ``docker_available``/``lxc_available``.
        """
        return True

    def collect(self) -> ContainerMetrics:
        with self._lock:
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
        with self._lock:
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
                self._docker_client = docker.from_env(timeout=5)
            self._docker_client.ping()
            return True
        except Exception:
            self._docker_client = None
            return False

    # ── Docker ───────────────────────────────────────────────────────────

    def _collect_docker(self) -> list[ContainerInfo]:
        containers: list[ContainerInfo] = []
        running: list[Any] = []
        try:
            if self._docker_client is None:
                import docker

                self._docker_client = docker.from_env(timeout=5)

            for c in self._docker_client.containers.list(all=True):
                # Retrieve the image name from attributes to avoid lazy-loading c.image API call
                image_name = ""
                if c.attrs:
                    image_name = c.attrs.get("Config", {}).get("Image") or ""
                    if not image_name:
                        img_id = c.attrs.get("Image") or ""
                        if img_id.startswith("sha256:"):
                            image_name = img_id[7:19]
                        else:
                            image_name = img_id[:12]
                if not image_name:
                    image_name = c.short_id

                containers.append(
                    ContainerInfo(
                        name=c.name or "",
                        container_id=c.short_id,
                        image=image_name,
                        status=c.status,
                        runtime="docker",
                    )
                )
                running.append(c)

            if self._stats_enabled and running:
                containers = self._merge_stats(containers, running)
        except Exception:
            log.debug("Docker collection failed", exc_info=True)
        return containers

    def _merge_stats(self, infos: list[ContainerInfo], running: list[Any]) -> list[ContainerInfo]:
        """Attach CPU/memory stats to running containers.

        ``stats(stream=False)`` blocks for ~1 s per container, so calls are
        fanned out across a small pool with an overall deadline; anything that
        doesn't answer in time keeps its ``None`` values.
        """
        by_id = {c.short_id: c for c in running if c.status == "running"}
        if not by_id:
            return infos

        stats: dict[str, tuple[float | None, int | None, int | None]] = {}
        with ThreadPoolExecutor(
            max_workers=min(len(by_id), 8), thread_name_prefix="raven-docker-stats"
        ) as pool:
            futures = {pool.submit(self._container_stats, c): cid for cid, c in by_id.items()}
            try:
                for future in as_completed(futures, timeout=_STATS_DEADLINE):
                    cid = futures[future]
                    try:
                        stats[cid] = future.result()
                    except Exception:
                        log.debug("Stats failed for container %s", cid, exc_info=True)
            except TimeoutError:
                log.debug("Docker stats deadline exceeded — reporting partial stats")

        return [
            replace(
                info,
                cpu_percent=stats[info.container_id][0],
                memory_usage=stats[info.container_id][1],
                memory_limit=stats[info.container_id][2],
            )
            if info.container_id in stats
            else info
            for info in infos
        ]

    @staticmethod
    def _container_stats(container: Any) -> tuple[float | None, int | None, int | None]:
        """Return ``(cpu_percent, memory_usage, memory_limit)`` for one container."""
        raw = container.stats(stream=False)

        cpu_percent: float | None = None
        try:
            cpu = raw["cpu_stats"]
            precpu = raw["precpu_stats"]
            cpu_delta = cpu["cpu_usage"]["total_usage"] - precpu["cpu_usage"]["total_usage"]
            system_delta = cpu.get("system_cpu_usage", 0) - precpu.get("system_cpu_usage", 0)
            if cpu_delta > 0 and system_delta > 0:
                ncpu = cpu.get("online_cpus") or len(cpu["cpu_usage"].get("percpu_usage") or [1])
                cpu_percent = round((cpu_delta / system_delta) * ncpu * 100.0, 1)
        except (KeyError, TypeError, ZeroDivisionError):
            pass

        mem_usage: int | None = None
        mem_limit: int | None = None
        try:
            mem = raw["memory_stats"]
            # Subtract page cache so the figure matches `docker stats`.
            cache = (mem.get("stats") or {}).get("cache", 0)
            mem_usage = max(0, mem["usage"] - cache)
            mem_limit = mem.get("limit")
        except (KeyError, TypeError):
            pass

        return cpu_percent, mem_usage, mem_limit

    # ── LXC ──────────────────────────────────────────────────────────────

    @staticmethod
    def _collect_lxc() -> list[ContainerInfo]:
        containers: list[ContainerInfo] = []
        try:
            process = subprocess.Popen(
                ["lxc", "list", "--format", "json"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                # Read output and wait with a timeout of 5 seconds
                stdout, stderr = process.communicate(timeout=5)
                # Check maximum size of output
                if len(stdout.encode("utf-8", errors="ignore")) > _LXC_MAX_OUTPUT:
                    log.warning(
                        "LXC output exceeded %d bytes",
                        _LXC_MAX_OUTPUT,
                    )
                    return containers
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                log.warning("LXC list command timed out")
                return containers
            except Exception:
                process.kill()
                raise

            if process.returncode != 0:
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
