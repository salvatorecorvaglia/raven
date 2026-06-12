"""CLI entry point for Raven.

Usage::

    raven              # TUI dashboard
    raven fetch        # Quick system summary
    raven web          # Web dashboard
    raven serve        # Remote monitoring agent
    raven print [MOD]  # Print stats to stdout
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from raven.config import RavenConfig



import urllib.parse


def remote_address_type(value: str) -> str:
    """Argparse type validator for remote host:port addresses."""
    url_str = value
    if not url_str.startswith(("http://", "https://")):
        url_str = f"http://{url_str}"
    try:
        parsed = urllib.parse.urlparse(url_str)
        if not parsed.hostname:
            raise ValueError("Hostname is required")
        if parsed.port is not None:
            if not (1 <= parsed.port <= 65535):
                raise ValueError("Port must be between 1 and 65535")
    except Exception as e:
        raise argparse.ArgumentTypeError(f"Invalid remote address format '{value}': {e}")
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="raven",
        description="Raven — cross-platform system monitor",
    )
    parser.add_argument(
        "--config",
        "-c",
        metavar="PATH",
        help="Path to raven.toml config file",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose debug logging",
    )
    parser.add_argument(
        "--remote",
        "-r",
        type=remote_address_type,
        metavar="HOST:PORT",
        help="Connect to a remote Raven agent",
    )


    sub = parser.add_subparsers(dest="command")

    # ── fetch ────────────────────────────────────────────────────────
    sub.add_parser("fetch", help="Quick system summary (neofetch-style)")

    # ── web ──────────────────────────────────────────────────────────
    web_p = sub.add_parser("web", help="Start the web dashboard")
    web_p.add_argument("--host", default=None, help="Bind host (default: from config)")
    web_p.add_argument(
        "--port", "-p", type=int, default=None, help="Bind port (default: from config)"
    )

    # ── serve ────────────────────────────────────────────────────────
    serve_p = sub.add_parser("serve", help="Start remote monitoring agent")
    serve_p.add_argument("--host", default=None, help="Bind host")
    serve_p.add_argument("--port", "-p", type=int, default=None, help="Bind port")

    # ── print ────────────────────────────────────────────────────────
    print_p = sub.add_parser("print", help="Print selected stats to stdout")
    print_p.add_argument(
        "modules",
        nargs="*",
        default=None,
        help=(
            "Module names to print (cpu, memory, disk, network, "
            "processes, users, sensors, containers, system_info)"
        ),
    )
    print_p.add_argument(
        "--format",
        "-f",
        choices=["text", "csv", "json"],
        default=None,
        help="Output format (default: from config)",
    )
    print_p.add_argument(
        "--once",
        action="store_true",
        help="Print once and exit (default)",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    """Main entry point."""
    import logging
    from raven.config import load_config

    parser = _build_parser()
    args = parser.parse_args(argv)

    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = load_config(args.config)


    command = args.command

    # ── fetch ────────────────────────────────────────────────────────
    if command == "fetch":
        from raven.fetch import run_fetch

        run_fetch(config)
        return

    # ── print ────────────────────────────────────────────────────────
    if command == "print":
        _cmd_print(args, config)
        return

    # ── web ──────────────────────────────────────────────────────────
    if command == "web":
        _cmd_web(args, config)
        return

    # ── serve ────────────────────────────────────────────────────────
    if command == "serve":
        _cmd_serve(args, config)
        return

    # ── default: TUI ─────────────────────────────────────────────────
    _cmd_tui(args, config)


# ── Sub-command handlers ─────────────────────────────────────────────────────


def _cmd_print(args: argparse.Namespace, config: RavenConfig) -> None:
    from raven.core.collector import Collector

    fmt = args.format or config.export.format
    modules = args.modules or None

    if args.remote:
        from raven.remote.client import RemoteCollector

        collector = RemoteCollector(args.remote)
    else:
        collector = Collector(config)

    snapshot = collector.collect()

    if fmt == "json":
        from raven.export.json_export import JsonExporter

        exporter = JsonExporter()
    elif fmt == "csv":
        from raven.export.csv_export import CsvExporter

        exporter = CsvExporter()
    else:
        from raven.export.text_export import TextExporter

        exporter = TextExporter()

    print(exporter.format(snapshot, modules))


def _cmd_web(args: argparse.Namespace, config: RavenConfig) -> None:
    import uvicorn

    from raven.web.server import create_app

    host = args.host if args.host is not None else config.web.host
    port = args.port if args.port is not None else config.web.port

    app = create_app(config)
    print(f"🐦‍⬛ Raven web dashboard → http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


def _cmd_serve(args: argparse.Namespace, config: RavenConfig) -> None:
    import uvicorn

    from raven.remote.server import create_remote_app

    host = args.host if args.host is not None else config.remote.host
    port = args.port if args.port is not None else config.remote.port

    app = create_remote_app(config)
    print(f"🐦‍⬛ Raven remote agent → http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


def _cmd_tui(args: argparse.Namespace, config: RavenConfig) -> None:
    remote_addr = getattr(args, "remote", None)
    if remote_addr:
        from raven.remote.client import RemoteCollector

        collector = RemoteCollector(remote_addr)
    else:
        from raven.core.collector import Collector

        collector = Collector(config)

    if not remote_addr:
        import threading
        import uvicorn

        if config.web.enabled:
            from raven.web.server import create_app
            web_app = create_app(config)
            t = threading.Thread(
                target=uvicorn.run,
                args=(web_app,),
                kwargs={
                    "host": config.web.host,
                    "port": config.web.port,
                    "log_level": "warning",
                },
                daemon=True,
            )
            t.start()

        if config.remote.enabled:
            from raven.remote.server import create_remote_app
            remote_app = create_remote_app(config)
            t = threading.Thread(
                target=uvicorn.run,
                args=(remote_app,),
                kwargs={
                    "host": config.remote.host,
                    "port": config.remote.port,
                    "log_level": "warning",
                },
                daemon=True,
            )
            t.start()

    from raven.tui.app import RavenApp

    app = RavenApp(collector=collector, config=config)
    app.run()



if __name__ == "__main__":
    main()
