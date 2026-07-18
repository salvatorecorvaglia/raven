# Contributing to Raven 🐦‍⬛

First off, thank you for considering contributing to Raven! It's people like you who make Raven a great cross-platform system monitor.

Please take a moment to review this document to make the contribution process smooth and efficient for everyone involved.

## Code of Conduct

By participating in this project, you agree to abide by our standards of respect, inclusivity, and collaboration. Please be kind and respectful in all interactions.

## How Can I Contribute?

### 🐛 Reporting Bugs
Before submitting a bug report:
1. Search the [existing Issues](https://github.com/salvatorecorvaglia/raven/issues) to ensure the bug hasn't already been reported.
2. If it's a new issue, use the **Bug Report** template when creating it.
3. Provide a clear, detailed description of the problem, steps to reproduce, and details about your operating system and environment.

### ✨ Suggesting Enhancements
We love new ideas! If you have a feature suggestion:
1. Search the [existing Issues](https://github.com/salvatorecorvaglia/raven/issues) to see if it has been discussed.
2. File a **Feature Request** issue detailing the problem your feature solves and how it should work.

### 🛠 Pull Requests
1. Fork the repository and create your branch from `main`.
2. Keep your PRs focused on a single change/feature.
3. Ensure the test suite passes and new tests are added for your changes.
4. Follow the project's code style and formatting standards.
5. Reference any related issues in the PR description (e.g., `Fixes #123`).

---

## Local Development Setup

Raven uses `uv` for lightning-fast Python virtual environment and package management.

### 1. Prerequisites
- Python 3.11 or newer.
- `uv` installed. If you don't have it, install it via:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Or via Homebrew (macOS)
  brew install uv
  ```

### 2. Environment Setup
Clone the repository and sync the development environment (including all extras and dev dependencies):
```bash
git clone https://github.com/salvatorecorvaglia/raven.git
cd raven

# Sync virtual environment and dependencies
uv sync --all-extras --dev
```

This creates a local `.venv` directory configured with all dependencies (including `docker` and `dev` tools like `pytest` and `ruff`).

### 3. Running Raven in Development
To run your development copy of Raven, prefix commands with `uv run`:
```bash
# Launch the TUI dashboard
uv run raven

# Launch the quick fetch summary
uv run raven fetch

# Launch the web dashboard
uv run raven web
```

---

## Code Quality & Guidelines

To maintain code quality, we enforce linting, formatting, and type safety rules.

### 🎨 Formatting and Linting
We use [Ruff](https://github.com/astral-sh/ruff) to lint and format our codebase. Before committing, run:
```bash
# Check for lint issues and automatically fix simple ones
uv run ruff check --fix

# Format code automatically
uv run ruff format
```
The CI pipeline will fail if Ruff checks or formatting fail.

### 🔒 Type Safety
This project uses PEP 484 type hints. If you add new parameters, functions, or classes, ensure they are properly typed.

### 🧵 Thread Safety
If your custom plugin maintains internal state, caches query results, or tracks execution ticks between `collect()` cycles, ensure it is thread-safe. Metric collection may run concurrently across background threads or async tasks. Use locks (like `threading.Lock` or `threading.RLock`) to guard mutable shared state inside your plugin subclass.

### 🔌 Custom Plugin Configuration & Discovery
Built-in and custom plugins are dynamically discovered from the `raven/plugins/` directory using `pkgutil.iter_modules`. Any new python file placed in `raven/plugins/` containing a subclass of `MonitorPlugin` is loaded automatically.

When implementing a custom plugin, you can optionally accept the global configuration by defining an `__init__(self, config=None)` constructor. The plugin manager automatically uses `inspect.signature` to check the parameters and pass the `RavenConfig` object if requested.

### 🛡️ Security Guidelines
- **API Authentication**: If you introduce new REST endpoints or WebSocket APIs, ensure they are protected by the API key security middleware.
- **Timing-Attack Resistance**: Always use timing-safe comparison functions like `hmac.compare_digest` when validating API keys, tokens, or credentials.
- **Obfuscated Browser Storage**: Never store clear-text API keys or sensitive credentials in client-side browser storage (e.g., `localStorage` or `sessionStorage`). Apply the existing pattern of XOR obfuscation with a secure salt.
- **Referrer Privacy**: Ensure all API responses include the `Referrer-Policy: no-referrer` header, and static web pages contain the `<meta name="referrer" content="no-referrer">` directive to avoid inadvertent credential or path leakage.

---

## Testing

We use [pytest](https://docs.pytest.org/) for automated testing.

- Place unit and integration tests in the [tests/](tests/) directory.
- Run the full test suite before submitting a PR:
  ```bash
  uv run pytest
  ```
- Make sure to add tests for any new features or bug fixes you implement.
- **Testing Authenticated Paths**: If you add or modify API/WebSocket endpoints, write tests verifying both authenticated (with valid key) and unauthenticated (missing or invalid key) flows.
- **Mocking and Sockets in Tests**: When writing integration tests for remote metric collection or daemon servers, avoid spinning up actual TCP sockets and uvicorn servers to reduce test runtime, avoid port conflicts, and eliminate flake. Instead, use `fastapi.testclient.TestClient` for synchronous route tests and `httpx.ASGITransport` coupled with `httpx.AsyncClient` for asynchronous client-server integration testing.
- **TUI Dashboard Testing**: For terminal dashboard TUI components, place integration tests in `tests/test_tui.py`. Use Textual's `app.run_test()` helper to verify widget mounting, layout structure, and panel presence without rendering a physical GUI.
- **Concurrency & Thread Safety**: Ensure the collector and plugins remain thread-safe by verifying behavior against the dedicated concurrency test suite (`tests/test_concurrency.py`). Plugins must not deadlock or raise exceptions when multiple collection cycles execute concurrently.
- **Cross-Platform Compatibility**: Raven targets **Linux, BSD, macOS, and Windows** across Python **3.11, 3.12, and 3.13**. Use `pytest.mark.skipif` to conditionally skip checks that depend on OS-specific commands or specs.

---

## Project Structure

Here is a quick overview of where different modules reside in the [raven/](raven/) package:
- `core/`: Core system monitoring modules, standard metric collectors, and background server runners.
- `plugins/`: Extensible plugin system. To add a new metric collector, place it here (see `README.md` for a plugin example).
- `tui/`: Textual-based terminal user interface components and styles (`.tcss`).
- `web/`: FastAPI web dashboard backend and static assets (HTML/CSS/JS).
- `remote/`: Server agent and client tools for remote metric synchronization.
- `export/`: CLI and programmatic data exporters (JSON, CSV, plaintext).
- `cli.py`: Command-line interface definition and parsing.

---

Happy coding! 🐦‍⬛
