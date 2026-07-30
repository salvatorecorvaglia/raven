# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Added Changelog and Security policy section links to `README.md`.

### Changed

- Modernized progress bar rendering in `render_bar` using box-drawing characters (`━` / `─`) and added configurable `filled_char` and `unfilled_char` parameters.
- Updated percentage threshold color palette in `color_for_percent` to modern hex values (`#00d2ff`, `#f59e0b`, `#ef4444`).
- Refactored `DiskWidget` in the TUI to utilize `render_bar` for standardized progress bar rendering.
- Streamlined `CpuWidget` and `MemoryWidget` TUI displays by removing redundant sparkline elements.
- Enhanced robustness of `color_for_percent`, `text_sparkline`, and `render_bar` to safely handle `None` percentage and history values.

### Fixed

- Updated utility test assertions in `tests/test_utils.py` to match new box-drawing progress bar characters and hex color codes.

## [0.7.0] - 2026-07-27

### Added

- Added unit tests for Docker daemon connection timeouts in `ContainersPlugin`.
- Added unit test coverage for TUI `ProcessTable` widget data updates.

### Changed

- Simplified process monitoring in `ProcessesPlugin` by utilizing `psutil.process_iter()` with pre-fetched field attributes and removing manual state/PID caching.
- Configured a 5-second connection timeout (`timeout=5`) when initializing `docker.from_env()` in `ContainersPlugin` to prevent hanging on unresponsive Docker daemons.
- Refactored Web Dashboard API key obfuscation helper functions (`obfuscateKey` / `deobfuscateKey`) in `app.js`.
- Refactored and streamlined contribution guidelines, setup steps, and project documentation across `CONTRIBUTING.md` and `README.md`.

### Fixed

- Cleaned up trailing whitespace across plugin implementations and test suites.

## [0.6.0] - 2026-07-18

### Added

- Added concurrency groups to CI and release workflows to cancel in-progress runs automatically.
- Added `Referrer-Policy: no-referrer` header in API responses via custom middleware and `<meta name="referrer" content="no-referrer">` in the Web Dashboard.
- Added WebSocket authentication tests verifying connection lifecycle with and without a valid API key.
- Added a dedicated concurrency test suite to verify thread-safe metric collection across multiple concurrent threads.

### Changed

- Replaced the hardcoded list of built-in plugins in `plugin_manager.py` with dynamic module discovery using `pkgutil.iter_modules`.
- Optimized concurrent metric collection by using non-blocking lock acquisition in the central coordinate `Collector` to avoid thread accumulation when a call hangs.
- Refactored `ProcessesPlugin` to fetch system PIDs using `psutil.pids()` and instantiate processes as needed, instead of iterating over `psutil.process_iter()`.
- Improved container metric collection in `ContainersPlugin` to use `subprocess.communicate` with a 5-second timeout for safer process execution and resource cleanup.
- Refined `CpuPlugin` overall CPU usage calculation to compute the average of per-core percentages, preventing inaccuracy on fast subsequent calls.
- Fixed a potential `RuntimeError: Set changed size during iteration` in `raven/core/api.py` by copying the active WebSockets set prior to broadcasting.

## [0.5.0] - 2026-07-12

### Added

- Added XOR obfuscation for API keys in storage (`sessionStorage` and `localStorage`) on the Web Dashboard to prevent clear text exposure.
- Added dark/light theme persistence check in the Web Dashboard via inline script in `index.html` to prevent flash of unstyled content (FOUC).
- Added `close_async()` in the `Collector` core module for clean asynchronous cleanup of collector resources.
- Added TUI integration tests in `tests/test_tui.py` to verify proper mounting and presence of all panel widgets.

### Changed

- Optimized process monitoring (`ProcessesPlugin`) by caching and skipping inaccessible PIDs (such as zombie or permission-restricted processes) to minimize redundant, costly system calls.
- Enhanced LXC container metric collection safety in `ContainersPlugin` by switching to `subprocess.Popen` and reading from stdout up to a hardcoded byte limit to avoid memory exhaustion from huge command outputs.
- Refactored `plugin_manager.py` to check constructor signatures via `inspect.signature` rather than relying on catching `TypeError` when checking if a plugin accepts `config`.
- Optimized resource usage by sharing a single collector instance between TUI/CLI and daemonized background servers (`start_background_servers`).
- Improved precision in the CPU monitor plugin (`CpuPlugin`) by querying `psutil.cpu_percent` directly with `percpu=False` for the overall CPU percent calculation instead of computing the average of per-core percentages.
- Simplified empty container layout messaging in `ContainerWidget` to "No containers detected".
- Improved remote collector integration tests by using `fastapi.testclient.TestClient` and `httpx.ASGITransport` instead of spinning up actual TCP sockets and uvicorn servers, reducing test run times and eliminating flake.

### Fixed

- Added proper TUI teardown handling in `RavenApp.on_unmount` to close the collector and release resources on exit.


## [0.4.0] - 2026-07-05

### Added

- Added timing-attack resistant API key authentication for remote monitoring servers (`serve` command) and the web interface (`web` command).
- Added an interactive Auth Modal overlay to the Web Dashboard for entering the API key upon connection failure (HTTP 4001 status), with key persistence in `sessionStorage` and `localStorage`.
- Added background server orchestration in `raven/core/runner.py` to daemonize web and remote server execution, decoupling uvicorn thread spawning from CLI routing.
- Added CLI/TUI synchronization to forward the configured API key to the client `RemoteCollector` automatically.
- Added integration and unit tests for authenticated remote connections and background runner daemon threads.


## [0.3.0] - 2026-06-22

### Added

- Added thread-safe locks (`threading.Lock` and `threading.RLock`) to `NetworkPlugin`, `ProcessesPlugin`, and `ContainersPlugin` to safeguard internal metrics caches and tickers during concurrent collections.
- Added comprehensive unit tests for container monitoring plugins under `tests/test_containers_plugin.py`.
- Added a configuration fallback test in `tests/test_config.py` to ensure scalar inputs for section configurations gracefully default.

### Changed

- Updated Textual TUI dashboard command routing to run the web/remote servers daemonized with `install_signal_handlers=False`, preventing signal registration errors in child threads.
- Refactored `Collector` core module cache lookup to fetch full system snapshots on cache expiration instead of checking double locks.
- Improved configuration parser in `raven/config.py` to gracefully fallback to default sub-configurations and warn when scalar values are supplied for configuration sections.
- Improved plugin class instantiation in `plugin_manager.py` to gracefully handle errors (`Exception` or `TypeError`) and skip the failing plugin instead of crashing.
- Optimized serialisation speed in exports by replacing dataclass `asdict` with a customized `serialize_model`.

### Fixed

- Resolved resource teardown during FastAPI application shutdown by awaiting `close_async()` on the metric collector inside the lifespan event.
- Prevented potential crashes in the CLI `fetch` summary, text exporter, and TUI battery widget (`sensor_widget.py`) when the battery percent is not available or returns `None`.
- Truncated mount points to 14 characters in `DiskWidget` layout to avoid visual overflow and text alignment issues.
- Handled cases in `ContainerWidget` where Docker and LXC are installed/available but no containers are found vs when the engines themselves are missing.

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