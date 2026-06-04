# Raven 🐦‍⬛

**A modern system monitor that works on Linux, BSD, macOS, and Windows.**

---

## Features

| Feature | Description |
|---|---|
| **TUI Dashboard** | Full-screen terminal UI with live-updating CPU, memory, disk, network, process, sensor, and container panels |
| **Web Dashboard** | Browser-based real-time dashboard with Chart.js sparklines, WebSocket streaming, glassmorphism design |
| **Quick Fetch** | Neofetch-style system summary with ASCII art |
| **REST API** | Full JSON API at `/api/v1/snapshot` and per-module endpoints |
| **Remote Monitoring** | Client–server mode — run `raven serve` on a remote host, connect with `raven --remote host:port` |
| **Multi-Format Export** | Print stats as plain text, CSV, or JSON |
| **Plugin Architecture** | Extensible monitoring via plugins — add new metric sources easily |
| **TOML Configuration** | Customise refresh rate, enabled modules, web/remote ports, process sorting |

---

## Quick Start

```bash
# Install
pip3 install -e .

# Launch TUI dashboard
raven

# Quick system summary
raven fetch

# Print CPU and memory as JSON
raven print cpu memory --format json

# Start web dashboard
raven web

# Start remote monitoring agent
raven serve --port 9090

# Connect TUI to remote host
raven --remote 10.0.0.5:9090
```

---

## Commands

```
raven                          Launch TUI dashboard (default)
raven fetch                    Quick neofetch-style summary
raven web [--host H] [--port P]  Start web dashboard
raven serve [--host H] [--port P]  Start remote agent
raven print [MODULES] [--format text|csv|json]  Print stats
raven --remote HOST:PORT       Connect to remote agent
raven --config PATH            Use custom config file
```

---

## Configuration

Raven looks for `raven.toml` in this order:
1. `--config` CLI flag
2. `./raven.toml` (current directory)
3. `~/.config/raven/raven.toml`

```toml
[general]
refresh_interval = 2     # seconds
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
host = "0.0.0.0"
port = 8080
api_key = ""             # empty = no auth

[remote]
host = "0.0.0.0"
port = 9090
api_key = ""

[export]
format = "text"          # text | csv | json

[processes]
max_display = 25
sort_by = "cpu"          # cpu | memory | pid | name
```

---

## REST API

When the web dashboard or remote agent is running:

```bash
# Full snapshot
curl http://localhost:8080/api/v1/snapshot

# Individual modules
curl http://localhost:8080/api/v1/cpu
curl http://localhost:8080/api/v1/memory
curl http://localhost:8080/api/v1/disk
curl http://localhost:8080/api/v1/network
curl http://localhost:8080/api/v1/processes
curl http://localhost:8080/api/v1/sensors
curl http://localhost:8080/api/v1/containers
curl http://localhost:8080/api/v1/system_info

# With API key
curl -H "X-API-Key: my-secret" http://localhost:8080/api/v1/snapshot
```

---

## TUI Keybindings

| Key | Action |
|---|---|
| `q` | Quit |
| `r` | Force refresh |
| `p` | Cycle process sort (CPU → Memory → PID → Name) |

---

## Writing a Plugin

Create a new file in `raven/plugins/`:

```python
from raven.plugins.base import MonitorPlugin
from dataclasses import dataclass

@dataclass(frozen=True)
class MyMetrics:
    value: float = 0.0

class MyPlugin(MonitorPlugin):
    name = "my_plugin"
    category = "custom"

    def is_available(self) -> bool:
        return True  # platform check

    def collect(self) -> MyMetrics:
        return MyMetrics(value=42.0)

PLUGIN_INFO = {
    "name": "my_plugin",
    "category": "custom",
    "class": MyPlugin,
}
```

---

## Docker Support

Install with Docker extras for container monitoring:

```bash
pip3 install -e ".[docker]"
```

---

## Requirements

- Python ≥ 3.11
- Works on Linux, macOS, Windows, FreeBSD

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 🔐 Security

If you discover a security vulnerability, please see our [Security Policy](SECURITY.md).

## 📝 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

---

**Author**: [Salvatore Corvaglia](https://github.com/salvatorecorvaglia)
