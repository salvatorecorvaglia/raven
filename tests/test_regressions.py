"""Regression tests for the bugs found in the v1.0.0 audit.

Each test is named for the audit finding it pins down, so a future change that
reintroduces one of these fails loudly rather than silently.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from raven.config import (
    GeneralConfig,
    ModulesConfig,
    RavenConfig,
    RemoteConfig,
    WebConfig,
    _dict_to_config,
)
from raven.core.collector import Collector
from raven.remote.client import RemoteCollector
from raven.remote.server import create_remote_app
from raven.web.server import create_app

# ── C1: non-ASCII API keys must 401, not 500 ─────────────────────────────────


def test_non_ascii_header_value_is_rejected_not_crashed():
    """Starlette decodes headers as latin-1, so a non-ASCII key can reach the
    middleware over the wire. hmac.compare_digest would raise TypeError on it."""
    cfg = RavenConfig(web=WebConfig(api_key="secret-key"))
    with TestClient(create_app(cfg)) as client:
        # Sent as raw bytes: httpx refuses to ASCII-encode a non-ASCII str.
        resp = client.get("/api/v1/snapshot", headers={"X-API-Key": "wrong-clé".encode("latin-1")})
    assert resp.status_code == 401


def test_non_ascii_configured_key_does_not_crash_every_request():
    """A server configured with an emoji key must still answer 401, not 500 —
    the configured side of compare_digest is what raised TypeError."""
    cfg = RavenConfig(web=WebConfig(api_key="chiave-segreta-🔑"))
    with TestClient(create_app(cfg)) as client:
        resp = client.get("/api/v1/snapshot", headers={"X-API-Key": "guess"})
    assert resp.status_code == 401


def test_non_ascii_key_over_websocket():
    key = "chiave-🔑"
    cfg = RavenConfig(web=WebConfig(api_key=key))
    with TestClient(create_app(cfg)) as client, client.websocket_connect("/ws/live") as ws:
        ws.send_text(key)
        assert "cpu" in ws.receive_json()


# ── C2: a shared collector must survive server shutdown ──────────────────────


def test_injected_collector_survives_app_shutdown(mock_config):
    """The TUI hands its collector to background servers; shutting the server
    down must not tear down the collector the TUI is still using."""
    collector = Collector(mock_config)
    try:
        with TestClient(create_app(mock_config, collector=collector)):
            pass  # enter + exit runs the full lifespan
        # Still usable after the app has shut down.
        assert collector.collect() is not None
    finally:
        collector.close()


def test_owned_collector_is_closed_on_shutdown(mock_config):
    """Conversely, a collector the app created is its own responsibility."""
    collector = Collector(mock_config)
    with TestClient(create_app(mock_config, collector=collector)):
        pass
    assert collector.collect() is not None  # shared: still alive
    collector.close()

    # An app that built its own collector shuts that collector's pool down.
    app = create_app(mock_config)
    owned = _collector_of(app)
    with TestClient(app):
        pass
    with pytest.raises(RuntimeError):
        owned._executor.submit(lambda: None)


def _collector_of(app):
    """Dig the collector out of the app's snapshot route closure."""
    for route in app.routes:
        closure = getattr(getattr(route, "endpoint", None), "__closure__", None) or ()
        for cell in closure:
            if isinstance(cell.cell_contents, Collector):
                return cell.cell_contents
    raise AssertionError("no Collector found on app")


# ── C3: --host must reach the app, not just uvicorn ──────────────────────────


def test_cli_host_override_reaches_open_bind_warning():
    """`raven web --host 0.0.0.0` with no API key must warn."""
    from raven.cli import main

    cfg = RavenConfig(web=WebConfig(host="127.0.0.1", api_key=""))
    with (
        patch("raven.cli.load_config", return_value=cfg),
        patch("raven.cli.uvicorn.run"),
        patch("raven.core.api.warn_open_bind") as mock_warn,
        patch("raven.web.server.warn_open_bind") as mock_warn_web,
    ):
        main(["web", "--host", "0.0.0.0"])

    called = mock_warn_web.call_args or mock_warn.call_args
    assert called is not None, "warn_open_bind was never called"
    assert called.args[0] == "0.0.0.0", "warning saw the config host, not the CLI override"


def test_cli_host_override_is_what_uvicorn_binds():
    from raven.cli import main

    cfg = RavenConfig(web=WebConfig(host="127.0.0.1", port=8080, api_key=""))
    with (
        patch("raven.cli.load_config", return_value=cfg),
        patch("raven.cli.uvicorn.run") as mock_run,
    ):
        main(["web", "--host", "0.0.0.0", "--port", "9999"])
    assert mock_run.call_args.kwargs["host"] == "0.0.0.0"
    assert mock_run.call_args.kwargs["port"] == 9999


# ── C4: disabled modules must not report zeros ───────────────────────────────


def test_disabled_module_is_404_not_fake_zero():
    """A disabled CPU module must not be indistinguishable from an idle CPU."""
    cfg = RavenConfig(modules=ModulesConfig(cpu=False))
    with TestClient(create_app(cfg)) as client:
        resp = client.get("/api/v1/cpu")
    assert resp.status_code == 404
    assert "not enabled" in resp.json()["detail"]


def test_enabled_module_still_serves_data():
    cfg = RavenConfig(modules=ModulesConfig(cpu=True))
    with TestClient(create_app(cfg)) as client:
        resp = client.get("/api/v1/cpu")
    assert resp.status_code == 200
    assert "percent_overall" in resp.json()["data"]


def test_health_advertises_active_modules():
    cfg = RavenConfig(modules=ModulesConfig(cpu=False))
    with TestClient(create_app(cfg)) as client:
        body = client.get("/health").json()
    assert "cpu" not in body["active_modules"]
    assert "memory" in body["active_modules"]


def test_collector_active_modules_excludes_disabled(mock_config):
    cfg = RavenConfig(modules=ModulesConfig(cpu=False, memory=True))
    collector = Collector(cfg)
    try:
        assert "cpu" not in collector.active_modules
        assert "memory" in collector.active_modules
        assert collector.collect_module("cpu") is None
    finally:
        collector.close()


# ── C5: RemoteCollector must not leak its async client ───────────────────────


@pytest.mark.asyncio
async def test_remote_collector_close_async_releases_async_client():
    client = RemoteCollector("http://localhost:9090")
    await client._get_async_client()
    assert client._async_client is not None
    await client.close_async()
    assert client._async_client is None


def test_remote_collector_sync_close_also_releases_async_client():
    """The TUI drives collect_async but tears down via close()."""
    import asyncio

    client = RemoteCollector("http://localhost:9090")
    asyncio.run(client._get_async_client())
    assert client._async_client is not None
    client.close()
    assert client._async_client is None


def test_remote_collector_close_is_idempotent():
    client = RemoteCollector("http://localhost:9090")
    client.close()
    client.close()


# ── C6: container plugin must stay loaded when Docker is down ────────────────


def test_container_plugin_stays_loaded_without_runtime():
    from raven.core.plugin_manager import get_enabled_plugins

    with patch("shutil.which", return_value=None), patch.dict("sys.modules", {"docker": None}):
        plugins = get_enabled_plugins(RavenConfig(modules=ModulesConfig(containers=True)))
    assert "containers" in {p.name for p in plugins}


def test_container_plugin_respects_config_disable():
    from raven.core.plugin_manager import get_enabled_plugins

    plugins = get_enabled_plugins(RavenConfig(modules=ModulesConfig(containers=False)))
    assert "containers" not in {p.name for p in plugins}


# ── M6: config errors are user errors, not tracebacks ────────────────────────


def test_missing_config_file_exits_cleanly(capsys):
    from raven.cli import main

    with pytest.raises(SystemExit) as exc:
        main(["-c", "/nonexistent/raven.toml", "fetch"])
    assert exc.value.code == 2
    assert "Config file not found" in capsys.readouterr().err


def test_invalid_config_value_exits_cleanly(tmp_path, capsys):
    from raven.cli import main

    cfg_file = tmp_path / "raven.toml"
    cfg_file.write_text("[general]\nrefresh_interval = 0\n")
    with pytest.raises(SystemExit) as exc:
        main(["-c", str(cfg_file), "fetch"])
    assert exc.value.code == 2
    assert "refresh_interval" in capsys.readouterr().err


def test_malformed_toml_exits_cleanly(tmp_path, capsys):
    from raven.cli import main

    cfg_file = tmp_path / "raven.toml"
    cfg_file.write_text("[general\nthis is not toml")
    with pytest.raises(SystemExit) as exc:
        main(["-c", str(cfg_file), "fetch"])
    assert exc.value.code == 2


def test_wrong_type_names_the_offending_key():
    """A string port must be reported by name, not as a bare TypeError."""
    with pytest.raises(ValueError, match="web.port must be an integer"):
        _dict_to_config({"web": {"port": "8080"}})


def test_wrong_type_for_bool_module_flag():
    with pytest.raises(ValueError, match="modules.cpu must be a boolean"):
        _dict_to_config({"modules": {"cpu": "yes"}})


def test_float_refresh_interval_is_accepted():
    cfg = _dict_to_config({"general": {"refresh_interval": 2.5}})
    assert cfg.general.refresh_interval == 2.5


# ── M7: global flags work on either side of the subcommand ───────────────────


def test_global_flags_accepted_after_subcommand(tmp_path):
    from raven.cli import _build_parser

    cfg_file = tmp_path / "raven.toml"
    cfg_file.write_text("[general]\nrefresh_interval = 3\n")
    parser = _build_parser()

    after = parser.parse_args(["print", "-c", str(cfg_file)])
    before = parser.parse_args(["-c", str(cfg_file), "print"])
    assert after.config == before.config == str(cfg_file)


def test_subcommand_does_not_clobber_root_global_flag(tmp_path):
    """argparse parents= would reset --config to None without SUPPRESS."""
    from raven.cli import _build_parser

    args = _build_parser().parse_args(["-c", "root.toml", "print"])
    assert args.config == "root.toml"


# ── S5: WebSocket client cap ─────────────────────────────────────────────────


def test_websocket_client_limit_is_enforced(monkeypatch):
    import raven.core.api as api_module

    monkeypatch.setattr(api_module, "MAX_WEBSOCKET_CLIENTS", 1)
    cfg = RavenConfig(web=WebConfig(api_key=""))
    with TestClient(create_app(cfg)) as client:
        with client.websocket_connect("/ws/live") as first:
            first.send_text("")
            first.receive_json()
            with pytest.raises(Exception):  # noqa: B017 - close code varies by transport
                with client.websocket_connect("/ws/live") as second:
                    second.receive_json()


# ── Remote agent parity ──────────────────────────────────────────────────────


def test_remote_agent_health_and_auth():
    cfg = RavenConfig(remote=RemoteConfig(api_key="agent-key"))
    with TestClient(create_remote_app(cfg)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/snapshot").status_code == 401
        assert client.get("/api/v1/snapshot", headers={"X-API-Key": "agent-key"}).status_code == 200


def test_general_config_defaults_are_valid():
    cfg = GeneralConfig()
    assert cfg.refresh_interval >= 1
    assert cfg.theme in ("dark", "light")
