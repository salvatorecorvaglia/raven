# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2026-06-19

### Fixed

- Upgraded Starlette to version 1.3.1 in `uv.lock` to address a Denial of Service vulnerability.

### Chore

- Upgraded `actions/checkout` to `v4` in GitHub Actions CI and release workflows.

## [0.2.0] - 2026-06-14

### Added

- Added persistent synchronous and asynchronous HTTP clients (`httpx.Client` / `httpx.AsyncClient`) for remote metric collection in `RemoteCollector`.

### Changed

- Optimized system info collection by caching static system details (`boot_time`, `hostname`, `os_name`, etc.) on plugin initialization rather than querying them on every collect tick.
- Optimized overall metrics collection using thread-safe double-checked caching in the central coordinator `Collector`.
- Optimized process monitoring by grouping queries inside a `psutil.Process.oneshot()` context to reduce syscall overhead.
- Optimized disk metric collection by introducing a blocklist for slow network and pseudo-filesystems (e.g., NFS, SMBFS, tmpfs, devtmpfs).
- Optimized network metrics collection by throttling socket connection count queries to once every 10 collect cycles.
- Optimized container metrics collection by extracting image names directly from config/attribute metadata to prevent lazy-loaded Docker API calls.
- Optimized the FastAPI web server by pre-loading the HTML dashboard template (`index.html`) in memory on startup.
- Optimized serialization performance by adding a custom `serialize_model` utility, bypassing the slow standard `dataclasses.asdict`.
- Standardized package name as `raven-monitor` across `pyproject.toml`, imports, and metadata.

### Fixed

- Bound test sockets to localhost (`127.0.0.1`) in `tests/test_client.py` to prevent external network exposure during testing.

### Chore

- Configured GitHub Actions CI and release workflows to use `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` for compatibility.

## [0.1.0] - 2026-06-12

### Added

- First implementation of Raven.