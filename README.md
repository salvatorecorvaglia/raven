# Raven 🐦‍⬛

**Cross-platform system monitor for Linux, BSD, macOS, and Windows**

**Raven** is a cross-platform, open-source system monitor written in Python that works on Linux, BSD, macOS, and Windows.

---

## ✨ Features

- 🖥 **Interactive TUI Dashboard**: A beautiful terminal dashboard powered by [Textual](https://github.com/Textualize/textual). Inspect CPU, memory, disk, network, active processes, users, sensors, and containers.
- 🌐 **Modern Web Dashboard**: A real-time web interface powered by FastAPI and WebSockets. Includes light/dark mode persistence, secure API key authentication with XOR obfuscation for client-side storage, and a smooth user experience.
- 📡 **Remote Monitoring Agent**: Run Raven as a remote server agent (`serve` mode) and fetch metrics securely via `RemoteCollector` over HTTP/WebSockets from a centralized Raven instance.
- 🚀 **Quick Summary (`fetch`)**: A quick, `neofetch`-style console summary of your system's hardware, OS, and current utilization.
- 📊 **Structured Exports (`print`)**: Print snapshots of system metrics to stdout in **Text**, **CSV**, or **JSON** formats, ideal for scripting, integrations, or cron jobs.
- 📦 **Container Support**: Native monitoring for Docker and LXC containers (memory, CPU, status, and metadata).
- 🔒 **Security-First**: Support for timing-attack resistant API key authentication, `Referrer-Policy: no-referrer` header protection, and safe/clean connection closures.

---

## 🚀 Quick Start

### Prerequisites

- **Python**: `3.11` or higher.
- **Package Manager**: [uv](https://github.com/astral-sh/uv) (recommended) or `pip`.

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/salvatorecorvaglia/raven.git
   cd raven
   ```

2. **Sync the workspace (using `uv`)**:
   ```bash
   uv sync --all-extras --dev
   ```

3. **Install the package (using `pip`)**:
   ```bash
   pip install -e .
   ```

---

## 🖥 Command Line Usage

Once installed, the `raven` executable will be available on your system path.

```bash
# Start the interactive TUI Dashboard (default)
raven

# Run the TUI connected to a remote Raven agent
raven --remote 127.0.0.1:9090

# Print a quick neofetch-style system summary
raven fetch

# Start the Web Dashboard server (default: port 8080)
raven web

# Start the Remote Monitoring Agent server (default: port 9090)
raven serve

# Print system stats directly to stdout (JSON format)
raven print --format json

# Print specific modules' metrics (e.g. cpu, memory)
raven print cpu memory
```

### Global CLI Options

- `-c PATH`, `--config PATH`: Path to a custom `raven.toml` configuration file.
- `-v`, `--verbose`: Enable verbose debug logging.
- `-r HOST:PORT`, `--remote HOST:PORT`: Connect to a remote Raven agent instead of inspecting the local system.

---

## 🛠 Configuration

Raven can be configured using a `raven.toml` file. The search order for configuration is:
1. `--config` / `-c` CLI flag (explicit path).
2. `./raven.toml` (current working directory).
3. `~/.config/raven/raven.toml` (user profile configuration).
4. Default built-in values.

A default configuration template is available in [raven.example.toml](raven.example.toml).

### Configuration Options Reference

```toml
[general]
refresh_interval = 2        # Seconds between updates (minimum: 1)
theme = "dark"              # Theme to apply: "dark" or "light"

[modules]
cpu = true                  # Enable/disable specific monitoring modules
memory = true
disk = true
network = true
processes = true
users = true
sensors = true
containers = true

[web]
enabled = false             # Automatically run web server in TUI background
host = "127.0.0.1"          # Host address to bind the web server
port = 8080                 # Port for the web server (1-65535)
api_key = ""                # API key for the dashboard (empty = no authentication)

[remote]
enabled = false             # Automatically run remote agent in TUI background
host = "127.0.0.1"          # Host address to bind the agent server
port = 9090                 # Port for the remote agent (1-65535)
api_key = ""                # API key for agent connection security

[export]
format = "text"             # Default export format: "text", "csv", or "json"

[processes]
max_display = 25            # Max processes to display in TUI and print output
sort_by = "cpu"             # Sort criteria: "cpu", "memory", "pid", "name"
```

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📜 Changelog

Detailed release history and version changes can be found in [CHANGELOG.md](CHANGELOG.md).

## 🔐 Security

If you discover a security vulnerability, please see our [Security Policy](SECURITY.md).

## 📝 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

---

**Author**: [Salvatore Corvaglia](https://github.com/salvatorecorvaglia)