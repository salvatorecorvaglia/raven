# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-12

### Added
- First implementation of Raven.
- Created a comprehensive test suite (21 unit/integration tests) under `tests/` covering configuration merging, models, parallel collectors, client parsers, exporters, and plugins.
- Configured pytest/asyncio in `pyproject.toml` and established mock infrastructure.
- Introduced a premium loading shimmer state and connection-lost toast UI to the web dashboard.
- Added type-safe `MetricCollector` protocol to standardize local/remote metric collections.

### Changed
- Refactored `ProcessTable` (TUI) and web dashboard DOM rendering (`app.js`) to perform element updates in-place, eliminating layout flickering and preserving user selection/scroll states.
- Optimized process monitoring collection (`processes.py`) to query lightweight stats first, retrieving heavy metadata (`cmdline`/`memory_rss`) only for the top processes.
- Parallelized collector plugin queries using a thread pool executor.
- Bound API servers to `127.0.0.1` by default and added warnings when exposing metrics on `0.0.0.0` without authentication.
- Single-sourced the package version using `importlib.metadata`.
- Extracted inline JavaScript styles into CSS variables/classes in `style.css`.
- Fixed web dashboard grid alignment by widening `#users-card` to match the containers card.

### Fixed
- Fixed first-render CPU usage returning `0.0%` by priming `psutil.cpu_percent` on module load.
- Corrected `--port 0` CLI argument handling to prevent falling back to defaults when specifying port zero.
- Secured API key validation against timing attacks using `hmac.compare_digest`.
- Restricted LXC subprocess output sizes to 10MB to prevent memory exhaustion attacks.
- Prevented potential client crashes on unexpected sensors payload fields by filtering incoming dictionary keys.
- Cached Docker and LXC software availability checks to reduce CPU overhead.

