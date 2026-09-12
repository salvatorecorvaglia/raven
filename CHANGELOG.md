# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-09-12

### Added

- Added `raven/core/broadcast.py`, isolating WebSocket fan-out and connection lifecycle management into `BroadcastHub`. Features per-client send timeouts (`WS_SEND_TIMEOUT`), a concurrent client cap (`MAX_WEBSOCKET_CLIENTS`), and a resilient broadcast loop that survives individual failed cycles without terminating the streaming server.
- Added a Vitest test suite for the Web Dashboard (`tests/web/dashboard.test.js`, `tests/web/lib.test.js`, `tests/web/render.test.js`) executed with `jsdom`, accompanied by a dedicated `web-test` workflow in GitHub Actions CI.
- Added `raven/web/static/lib.js` as a UMD module containing pure formatting, sorting, rate calculation, container status checks, and key obfuscation utilities shared between the Web Dashboard and the Vitest test suite without requiring a build step.
- Added wire snapshot trimming via `serialize_snapshot()` in `raven/core/api.py`: drops unrendered `cmdline` data (~70% payload reduction) and caps processes to `max_display` for browser dashboards and WebSocket frames, while introducing `?full=true` for remote CLI clients needing complete exports.
- Added `set_collect_cmdline` to `Collector` and `ProcessesPlugin`, making command-line data collection opt-in (requested only by CSV and JSON exporters) and avoiding costly per-process filesystem reads during routine monitoring.
- Expanded the `MetricCollector` protocol (`raven/core/protocols.py`) to include `active_modules`, `last_collected_at`, and `collect_module_async`. Updated `RemoteCollector` (`raven/remote/client.py`) to satisfy this full protocol, automatically discovering `active_modules` via upstream `/health` and querying `?full=true` snapshots.
- Added remote agent support to `raven fetch` (`raven --remote <addr> fetch`), displaying a live formatted console summary of a remote host.
- Added `RemoteUnavailable` error handling in `raven/cli.py`, providing actionable diagnostics (such as prompting for an API key on HTTP 401) instead of raw tracebacks when remote agents fail or reject connections.
- Added CLI module validation in `raven print --modules`, rejecting unrecognized module names with a list of valid modules rather than silently outputting nothing.
- Added CLI guard preventing `--remote` usage with `raven web` and `raven serve`, surfacing an informative error explaining that server commands must run directly on the host being monitored.
- Added interactive theme toggling in the TUI (`t` key) to switch between light and dark themes on the fly.
- Added a visual `.stale` dashboard state in `dashboard.tcss` (reduced opacity and warning-colored header border) in the TUI when collection fails, paired with single-event transition toasts instead of spamming warning notifications on every tick.
- Added a "Retry" button beside the Web Dashboard status badge when reconnection backoff attempts are exhausted, avoiding requiring a full page refresh.
- Added an explanatory status note (`#process-note`) below the Web Dashboard process table clarifying when rows are truncated and indicating agent ranking vs local browser sorting.
- Added `sort_by` and severity `thresholds` (`percent` and `temp`) to the `/health` endpoint payload, ensuring the Web Dashboard dynamically mirrors the agent's configured ranking and alert thresholds.
- Added `ContainerInfo.is_running` property and `RUNNING_STATUSES` constant in `raven/core/models.py` to standardize container running state detection across the TUI, Web Dashboard, and console fetch summary.

### Changed

- `CpuPlugin` now samples CPU utilization by comparing against its own instance-retained `cpu_times` reading (`_percentages()`), rather than relying on `psutil.cpu_percent(interval=0)`. Because the collector executes plugins across rotating worker threads in a pool, `psutil`'s thread-local baseline previously reported 0.0% or inaccurate intervals whenever a plugin landed on a different thread.
- `ProcessesPlugin` now returns a `ProcessListing` (a `list` subclass carrying `.total`), ensuring the host's untruncated process count travels atomically with the snapshot rather than being read off the plugin object from another thread.
- Reordered HTTP middleware in `raven/core/api.py` so security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`) are applied outermost, guaranteeing they are attached even when requests fail authentication with HTTP 401.
- Expanded `_is_public_bind` in `raven/core/api.py` using Python's `ipaddress` module to detect IPv6 wildcards (`::`), empty strings, and explicit non-loopback addresses, ensuring `warn_open_bind` triggers for all insecure interfaces without an API key.
- Nested list serialization in CSV export (`csv_export.py`) now derives safety caps from `EXPORT_LIMITS` via `_nested_cap`, aligning partition and interface limits with `text_export.py`.
- Rich console markup in `raven/fetch.py` is now escaped with `rich.markup.escape()` across user names, hostnames, OS info, mountpoints, interface names, and sensor labels to prevent markup parsing errors.
- Web Dashboard status badge now shows "Authenticating…" upon WebSocket connection and delays the "Live" state until the first frame confirms the API key was accepted.

### Fixed

- Fixed `Collector._inflight` task management in `raven/core/collector.py`: completed futures are no longer reused on subsequent cycles (which previously replayed stale data and halved effective refresh rate), and finished tasks are pruned in a `finally` block to prevent pinning completed future objects.
- Fixed asynchronous collection methods (`collect_async`, `collect_module_async`, `collect_processes_async`) blocking the default event loop executor by redirecting them to the collector's dedicated `_async_executor`.
- Fixed memory and callback accumulation in `Collector` by replacing repeated `atexit.register` calls with a module-level set of weak references (`_LIVE_COLLECTORS`).
- Fixed plugin loader `_load_plugin_module` in `raven/core/plugin_manager.py` to only load `MonitorPlugin` subclasses defined directly within the target module (`obj.__module__ == fqn`), preventing imported sibling plugin classes from being loaded mistakenly.
- Fixed Docker connection pool leak in `ContainersPlugin.close()` by explicitly closing `_docker_client`.
- Fixed potential out-of-memory denial of service in `ContainersPlugin` LXC inspection: replaced `subprocess.Popen.communicate()` with a streaming bounded reader `_read_capped()` that aborts if output exceeds `_LXC_MAX_OUTPUT` (10 MB).
- Fixed unhandled cleanup task cancellations and exceptions in `RemoteCollector.close()`, logging warnings if background connection closure fails.
- Fixed palette memory leak in `raven/tui/theme.py`: converted the module-level `_cache` into a `weakref.WeakKeyDictionary` keyed by app instance.
- Fixed potential `TypeError` when formatting load averages in `text_export.py`, `fetch.py`, and `CpuWidget` on platforms that report partial or `None` load average tuples.
- Fixed "+N more" label in `SensorWidget` and Web Dashboard temperature list to accurately display "+N more temperatures" instead of "+N more sensors".

## [1.3.0] - 2026-09-05

### Added

- Added `raven/tui/theme.py`, resolving Textual design tokens (`$text-primary`, `$text-success`, …) into concrete colours for dashboard widgets. Rich `Text` styles cannot name a token — `Static.update()` parses them through Rich's colour parser — so the token classes in `dashboard.tcss` could never have applied to inline spans.
- Added `raven/core/limits.py` as the single source of truth for how many rows each surface shows (`DASHBOARD_LIMITS` for the TUI panels and web cards, `EXPORT_LIMITS` for `raven print`), replacing inline slice caps in the widgets and the text exporter.
- Added `display_limits` to the `/health` payload, so the Web Dashboard truncates the same lists at the same point as the TUI (mirroring how `max_display` is already shared).
- Added `level_for_percent` and `level_for_temp` to `raven/core/utils.py`, separating threshold logic from colour choice so the TUI, console output, and web dashboard can share thresholds while rendering them differently.
- Added `truncate_path` to `raven/core/utils.py`, truncating from the left so sibling mount paths stay distinguishable.
- Added RSS and Threads columns to the Web Dashboard process table, matching the columns the TUI has always shown.
- Added "+N more" notices to the partition, interface, temperature, fan, container, and user lists in the TUI and Web Dashboard, so a capped list reads as capped rather than complete.
- Added an `empty_color` parameter to `render_bar`, letting the TUI colour a bar's unfilled half from the active theme instead of Rich's `dim`.
- Added `:focus-visible` outlines for the Web Dashboard's sortable table headers, theme toggle, primary button, and auth inputs.
- Added TUI regression tests covering dashboard grid geometry, panel content fitting its grid cell, and widget colours changing with the theme.

### Changed

- TUI widgets now take every colour from the active theme rather than hardcoded literals (`bold cyan`, `bright_white`, `#00d2ff`), via the new `section_header`/`themed_bar` helpers.
- Web Dashboard surface colours painted over a themed background (headers, table headers, progress tracks, row tints, toasts, inputs) now route through named tokens (`--header-bg`, `--th-bg`, `--track-bg`, `--row-tint`, …) declared in both themes.
- `--accent-cyan` darkens to `#0369a1` in the light theme only, where it carries small uppercase text that `#0284c7` left at 3.4:1.
- Web Dashboard process sorting now follows `raven/core/sort.py`: the same key names, field mapping, case-insensitive name comparison, and per-key default direction (PID and Name ascend; CPU, MEM, RSS, and Threads descend) instead of always starting descending.
- Chart line colours in the Web Dashboard now follow the theme, rather than staying dark-theme colours while their axes flipped.
- The Web Dashboard containers card now reports "No container runtime detected" when neither Docker nor LXC is available, instead of "No containers detected" — which read as a healthy host running nothing. Matches `ContainerWidget`, which hides its panel outright.
- An unknown battery charge now shows as "Unknown" in the Web Dashboard rather than a critical-coloured 0%, matching the TUI and `raven fetch`.
- `html { font-size }` is now `87.5%` rather than a fixed `14px`, preserving the intended density while still scaling with the reader's browser font-size setting (WCAG 1.4.4).
- Dimming of the Web Dashboard during a dropped connection softened from `0.65` to `0.85`: stale values are still worth reading.
- `cursor: pointer` on Web Dashboard table headers is now scoped to `th[data-sort]`, so the unsortable Status column no longer advertises a click it does not handle.
- Removed the never-applied `.card-small` and `.updating` CSS rules, and extended the card entry-animation stagger to cover all eight cards rather than five.

### Fixed

- Fixed the TUI dashboard reserving a full grid row for its 3-cell-tall header. `dashboard.tcss` declared `grid-size: 4 5` with no `grid-rows`, so every row took an equal share of the height, leaving 8 blank cells above the CPU panel on a 45-row terminal.
- Fixed `#process-panel`'s `height: 1fr` having no effect, since its grid row was already a fixed fraction: the process list now absorbs the leftover height instead of splitting it evenly with the fixed-content panels (10 to 16 rows at 140x45).
- Fixed the TUI light theme being effectively unreadable. Widget colours were dark-theme literals, leaving header text at 1.44:1 and progress bars at 1.26:1 against `textual-light`'s surface; every rendered span now clears 3:1 in both themes.
- Fixed Web Dashboard rules that painted literal dark values no light-theme override touched: the page header and table header stayed near-black (putting their text at 2.52:1 and 3.47:1), and every progress track and row tint became white-on-white.
- Fixed Web Dashboard process table zebra striping being set at `rgba(255, 255, 255, 0.01)`, an alpha low enough to render as nothing in either theme.
- Fixed `#users-card` overriding its own responsive rules: the rule sat after the media queries, and since a media query adds no specificity it won its span back at every width — forcing an implicit second column into the single-column grid below 640px.
- Fixed unbounded growth of the Web Dashboard's per-interface rate baselines as VPN and tether interfaces come and go, the same leak `NetworkWidget` already prunes.
- Fixed `DiskWidget` truncating mount points from the right, which rendered sibling APFS volumes as several identical `/System/Volume` rows.

## [1.2.0] - 2026-08-25

### Added

- Added a warning (log entry and stderr message) when a loaded `raven.toml` contains a plaintext `api_key` but the file is group/world-readable, prompting the user to `chmod 600` it.
- Added CSV export sanitization against formula injection: fields beginning with `=`, `+`, `-`, `@`, tab, or carriage return (e.g. from attacker-influenceable process names or container labels) are now prefixed with a quote before reaching spreadsheet apps.
- Centralized process sort-key definitions into a shared `raven/core/sort.py` module, replacing duplicated sort maps in the exporters, `ProcessesPlugin`, and `ProcessTable`.
- Added on-demand process re-sorting (`Collector.collect_processes` / `collect_processes_async`) so cycling the TUI's process sort (`p`) re-collects and re-truncates the list instead of re-sorting an already-truncated cached slice.
- Added a `MonitorPlugin.close()` lifecycle hook and inflight-future tracking in `Collector`, so plugin resources are released on shutdown and a stalled plugin call is no longer resubmitted on every collection cycle.
- Added keyboard focus trapping and ARIA attributes (`role="dialog"`, `aria-modal`, `aria-labelledby`) to the Web Dashboard authentication modal.
- Added test coverage for background server orchestration, on-demand process sorting, plugin inflight tracking, config permission warnings, and export process-count consistency.

### Changed

- CSV and JSON exporters now derive their process list from the same `sorted_processes()` helper as the text exporter, instead of dumping the raw pre-truncation snapshot.
- `ContainersPlugin` now reuses a single `ThreadPoolExecutor` across collection cycles instead of creating and tearing down a new pool every refresh interval.
- Standardized TUI widget section headers (CPU, Memory, Disk, Network, etc.) through a shared `section_header` helper.
- `NetworkWidget` now discards rate-tracking state for interfaces that disappear (e.g. VPN/tether disconnects), preventing unbounded growth over long-running TUI sessions.

### Fixed

- Fixed CSV and JSON export process counts being inconsistent with the text exporter's `max_display`/`sort_by`-truncated list.
- Fixed a connection-pool leak in `RemoteCollector.close()` when called from within a running event loop; cleanup is now scheduled on the loop instead of dropped.

## [1.1.0] - 2026-08-12

### Added

- Vendorized Chart.js (`vendor/chart.umd.min.js`) in the Web Dashboard static assets to enable fully offline and air-gapped web monitoring without external CDN dependencies.
- Added inline theme initialization script (`theme-init.js`) to the Web Dashboard to eliminate theme flashing during initial page load.
- Added `mypy` static type checking and `pytest-cov` coverage reporting to `pyproject.toml` with an 80% minimum coverage threshold.
- Added automated dependency security auditing using `pip-audit` and coverage artifact uploads to the GitHub Actions CI workflow.
- Added comprehensive feature and regression test suites (`tests/test_features.py` and `tests/test_regressions.py`).

### Changed

- Enforced explicit `utf-8` encoding for all file I/O operations (config parsing, metric export files, web template loading) for consistent cross-platform behavior.
- Unified plugin initialization across `plugin_manager.py` and `collector.py` and enabled lazy container metric querying in `ContainersPlugin` to prevent startup delay.
- Configured recursive static asset inclusions (`static/**/*`) in `pyproject.toml` to ensure nested vendor assets are bundled in wheel distribution packages.
- Restricted CI workflow `cancel-in-progress` to pull request events.

### Fixed

- Enhanced robustness of system monitoring plugins (`network`, `processes`, `sensors`, `users`) with generic exception handling and explicit attribute checks to prevent `AttributeError` or unhandled exceptions on non-standard OS environments.

## [1.0.0] - 2026-08-06

### Chore

- Promoted package version to 1.0.0 for initial official PyPI release.

## [0.7.1] - 2026-07-30

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