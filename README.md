# Raven 🐦‍⬛

**A system monitor that works on Linux, BSD, macOS, and Windows.**

---

## 🌟 Key Features

* **⚡ Gorgeous Dashboards**:
  * **TUI Dashboard**: Built with [Textual](https://textual.textualize.io/), offering smooth animations, color themes, real-time widgets, and flicker-free updates.
  * **Web Dashboard**: An elegant web UI powered by FastAPI and Vanilla HTML/CSS/JS. Features premium loading shimmers, connection status toasts, and dynamic charts.
* **🐦‍⬛ Neofetch-style Fetch**: A quick terminal command to fetch system hardware specs, platform info, and resources.
* **🔒 Remote Monitoring**: Run a secure agent on a remote server with timing-attack resistant API key authentication, and visualize its metrics locally.
* **🔌 Extensible Plugins**: Easily write your own metrics collectors by inheriting from [MonitorPlugin](file:///Users/salvatorecorvaglia/github/raven/raven/plugins/base.py#L13).
* **📈 High Performance**: Metrics are queried in parallel via thread pools, with smart caching and lightweight process queries to minimize CPU overhead.
* **📥 Multi-format Exporting**: Print metrics directly to your terminal or save them as CSV, JSON, or plaintext.

---

## 🛠 Project Structure

Raven is structured cleanly to separate collection logic, plugins, and frontends:

* [raven/cli.py](file:///Users/salvatorecorvaglia/github/raven/raven/cli.py): CLI routing and argument definitions.
* [raven/config.py](file:///Users/salvatorecorvaglia/github/raven/raven/config.py): TOML configuration schemas and verification logic.
* [raven/core/](file:///Users/salvatorecorvaglia/github/raven/raven/core): Central coordinator containing the collector agent, type definitions, and standard protocol interfaces.
* [raven/plugins/](file:///Users/salvatorecorvaglia/github/raven/raven/plugins): Discovered monitoring plugins (CPU, Memory, Disk, Containers, Network, Sensors, Processes, etc.).
* [raven/tui/](file:///Users/salvatorecorvaglia/github/raven/raven/tui): Textual terminal widgets and layout CSS stylesheets (`.tcss`).
* [raven/web/](file:///Users/salvatorecorvaglia/github/raven/raven/web): FastAPI backend and static web dashboard assets.
* [raven/remote/](file:///Users/salvatorecorvaglia/github/raven/raven/remote): Server agent and client tools for remote metric sync.
* [raven/export/](file:///Users/salvatorecorvaglia/github/raven/raven/export): Formatted data exporters.

---

## 🚀 Getting Started

### 1. Prerequisites
* **Python 3.11+**
* `uv` (recommended) or `pip`

### 2. Installation & Setup
To install dependencies and prepare the environment:

```bash
# Clone the repository
git clone https://github.com/salvatorecorvaglia/raven.git
cd raven

# Sync virtual environment and download dependencies
uv sync --all-extras --dev
```

---

## 💻 Usage & CLI Guide

Raven offers a simple command-line structure routed through [raven/cli.py](file:///Users/salvatorecorvaglia/github/raven/raven/cli.py):

### 1. Start the TUI (Default)
Run Raven with no arguments to launch the Textual TUI dashboard:
```bash
uv run raven
```

### 2. Start the Web Dashboard
Expose a web-based dashboard utilizing FastAPI:
```bash
uv run raven web
# Options:
#   --host Hostname to bind to (e.g. 127.0.0.1)
#   --port Port to run server on (e.g. 8080)
```

### 3. Start a Remote Monitoring Agent
To monitor a remote server, run the daemon agent on the remote host:
```bash
uv run raven serve --host 127.0.0.1 --port 9090
```

### 4. Connect to a Remote Agent
You can direct your TUI, Web server, or exporters to read metrics from a running remote agent:
```bash
uv run raven --remote http://192.168.1.50:9090
```

### 5. Fetch a Quick System Summary
Get a quick `neofetch`-style output of your server specifications:
```bash
uv run raven fetch
```

### 6. Export Metrics to Stdout
Print system details to the terminal in JSON, CSV, or formatted text:
```bash
# Print all modules once as text
uv run raven print

# Print specific modules formatted as JSON
uv run raven print cpu memory --format json
```

---

## ⚙️ Configuration

Raven searches for settings in the following order:
1. `--config` / `-c` CLI option.
2. `./raven.toml` in the current working directory.
3. `~/.config/raven/raven.toml`.
4. Fall back to internal defaults.

Refer to [raven.example.toml](file:///Users/salvatorecorvaglia/github/raven/raven.example.toml) for customising ports, intervals, enabled modules, and security parameters:

```toml
[general]
refresh_interval = 2        # seconds between updates
theme = "dark"

[modules]
cpu = true
memory = true
disk = true
network = true
processes = true
users = true
sensors = true
containers = true

[web]
enabled = false
host = "127.0.0.1"
port = 8080
api_key = ""                # Empty = no authentication

[remote]
enabled = false
host = "127.0.0.1"
port = 9090
api_key = ""
```

---

## 🔌 Creating Custom Plugins

All metrics collection modules are structured as plugins. To add your own custom collector:

1. Create a Python file under the [raven/plugins/](file:///Users/salvatorecorvaglia/github/raven/raven/plugins) directory.
2. Subclass [MonitorPlugin](file:///Users/salvatorecorvaglia/github/raven/raven/plugins/base.py#L13) and implement the abstract methods:

```python
from raven.plugins.base import MonitorPlugin

class CustomMetricsPlugin(MonitorPlugin):
    name = "my_custom_metrics"
    category = "general"

    def is_available(self) -> bool:
        # Check system compatibility or dependencies here
        return True

    def collect(self) -> dict:
        # Collect and return your metrics
        return {
            "custom_metric_1": 42,
            "status": "online"
        }
```

3. Enable or customize your module inside your `raven.toml` under the `[modules]` header.

---

## 🧪 Testing & Development

We use `pytest` for automated test suites. Before submitting pull requests, run:

```bash
# Run the test suite
uv run pytest

# Check code formatting & lint issues
uv run ruff check

# Apply formatting
uv run ruff format
```

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 🔐 Security

If you discover a security vulnerability, please see our [Security Policy](SECURITY.md).

## 📝 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

---

**Author**: [Salvatore Corvaglia](https://github.com/salvatorecorvaglia)
