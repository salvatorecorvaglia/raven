"""Tests for the behaviour the docs promise: theming, process limits,
container stats, and export formatting."""

from unittest.mock import MagicMock, patch

import pytest

from raven.config import GeneralConfig, ModulesConfig, ProcessesConfig, RavenConfig
from raven.core.models import ProcessInfo, SystemSnapshot
from raven.core.utils import color_for_temp
from raven.export import EXPORT_FORMATS, get_exporter
from raven.plugins.containers import ContainersPlugin
from raven.plugins.processes import ProcessesPlugin
from raven.tui.app import RavenApp


def _snapshot_with(n: int) -> SystemSnapshot:
    """Snapshot with *n* processes of descending CPU and ascending memory."""
    return SystemSnapshot(
        processes=[
            ProcessInfo(
                pid=i,
                name=f"proc{i:03d}",
                cpu_percent=float(n - i),
                memory_percent=float(i),
            )
            for i in range(n)
        ],
        process_count=n * 10,
    )


# ── M1: the plugin must sort by the configured key before truncating ─────────


def test_processes_plugin_sorts_by_configured_key():
    cfg = RavenConfig(processes=ProcessesConfig(sort_by="memory", max_display=5))
    plugin = ProcessesPlugin(cfg)
    procs = plugin.collect()
    mem = [p.memory_percent for p in procs]
    assert mem == sorted(mem, reverse=True), "memory sort not applied before truncation"


def test_processes_plugin_sort_by_pid_is_ascending():
    cfg = RavenConfig(processes=ProcessesConfig(sort_by="pid"))
    pids = [p.pid for p in ProcessesPlugin(cfg).collect()]
    assert pids == sorted(pids)


def test_processes_plugin_reports_untruncated_total():
    plugin = ProcessesPlugin(RavenConfig(processes=ProcessesConfig(max_display=1)))
    procs = plugin.collect()
    assert plugin.total_count >= len(procs)


# ── U3: process_count is the host total, not the truncated length ────────────


def test_snapshot_process_count_is_independent_of_list_length():
    snap = _snapshot_with(3)
    assert len(snap.processes) == 3
    assert snap.process_count == 30


def test_remote_client_round_trips_process_count():
    from raven.core.utils import serialize_model
    from raven.remote.client import RemoteCollector

    parsed = RemoteCollector._parse(serialize_model(_snapshot_with(4)))
    assert parsed.process_count == 40


# ── M5: exporters honour max_display and sort_by ─────────────────────────────


def test_text_exporter_respects_max_display():
    cfg = RavenConfig(processes=ProcessesConfig(max_display=3, sort_by="cpu"))
    out = get_exporter("text", cfg).format(_snapshot_with(50), modules=["processes"])
    listed = [ln for ln in out.splitlines() if "proc" in ln]
    assert len(listed) == 3


def test_text_exporter_respects_sort_by_memory():
    cfg = RavenConfig(processes=ProcessesConfig(max_display=3, sort_by="memory"))
    out = get_exporter("text", cfg).format(_snapshot_with(50), modules=["processes"])
    listed = [ln for ln in out.splitlines() if "proc" in ln]
    # Highest memory_percent is the highest index.
    assert "proc049" in listed[0]


def test_text_exporter_shows_shown_of_total():
    cfg = RavenConfig(processes=ProcessesConfig(max_display=2))
    out = get_exporter("text", cfg).format(_snapshot_with(10), modules=["processes"])
    assert "(2 of 100)" in out


def test_exporter_registry_covers_all_documented_formats():
    for fmt in EXPORT_FORMATS:
        exporter = get_exporter(fmt)
        assert exporter.name == fmt
        assert isinstance(exporter.format(_snapshot_with(2)), str)


def test_unknown_format_falls_back_to_text():
    assert get_exporter("nonsense").name == "text"


# ── M4: theme is applied, not merely validated ───────────────────────────────


@pytest.mark.asyncio
async def test_tui_applies_light_theme(mock_config, mock_collector):
    mock_config.general.theme = "light"
    app = RavenApp(collector=mock_collector, config=mock_config)
    async with app.run_test():
        assert app.theme == "textual-light"


@pytest.mark.asyncio
async def test_tui_applies_dark_theme(mock_config, mock_collector):
    mock_config.general.theme = "dark"
    app = RavenApp(collector=mock_collector, config=mock_config)
    async with app.run_test():
        assert app.theme == "textual-dark"


def test_tui_stylesheet_uses_design_tokens():
    """Hardcoded hex would override the theme and defeat `general.theme`."""
    import re
    from pathlib import Path

    css = (Path(__file__).parent.parent / "raven/tui/dashboard.tcss").read_text(encoding="utf-8")
    assert not re.findall(r"#[0-9a-fA-F]{6}", css)
    assert "$surface" in css


def test_health_reports_configured_theme():
    from fastapi.testclient import TestClient

    from raven.web.server import create_app

    cfg = RavenConfig(general=GeneralConfig(theme="light"))
    with TestClient(create_app(cfg)) as client:
        assert client.get("/health").json()["theme"] == "light"


def test_theme_init_runs_before_paint():
    """The theme script must run at the top of <body>, not on DOMContentLoaded,
    or light-theme users see a dark flash first."""
    from pathlib import Path

    static = Path(__file__).parent.parent / "raven/web/static"
    html = (static / "index.html").read_text(encoding="utf-8")
    script = (static / "theme-init.js").read_text(encoding="utf-8")

    body_at = html.index("<body")
    assert html.index("theme-init.js") > body_at, "must be inside <body>"
    # Nothing renderable may precede it inside <body>.
    preamble = html[body_at : html.index("theme-init.js")]
    assert "<header" not in preamble and "<main" not in preamble
    assert "DOMContentLoaded" not in script, "deferring the class defeats the purpose"
    assert "document.body.classList.add" in script


# ── M5 (web): the dashboard honours the agent's max_display ──────────────────


def test_health_reports_max_display():
    from fastapi.testclient import TestClient

    from raven.web.server import create_app

    cfg = RavenConfig(processes=ProcessesConfig(max_display=7))
    with TestClient(create_app(cfg)) as client:
        assert client.get("/health").json()["max_display"] == 7


def test_dashboard_has_no_hardcoded_process_limit():
    from pathlib import Path

    js = (Path(__file__).parent.parent / "raven/web/static/app.js").read_text(encoding="utf-8")
    assert "sorted.slice(0, maxDisplay)" in js
    assert "const displayLimit = 40" not in js


# ── U7: temperatures use trip points, not the percentage scale ───────────────


def test_temp_color_prefers_sensor_trip_points():
    # 55 °C would be "warn" on the 50/80 percentage scale, but it is well
    # under this sensor's 90 °C high point.
    assert color_for_temp(55.0, high=90.0, critical=100.0) == "#00d2ff"
    assert color_for_temp(95.0, high=90.0, critical=100.0) == "#f59e0b"
    assert color_for_temp(101.0, high=90.0, critical=100.0) == "#ef4444"


def test_temp_color_fallback_when_no_trip_points():
    assert color_for_temp(40.0) == "#00d2ff"
    assert color_for_temp(75.0) == "#f59e0b"
    assert color_for_temp(90.0) == "#ef4444"


# ── M9: container CPU/memory ─────────────────────────────────────────────────


def _docker_mock(stats_payload):
    container = MagicMock()
    container.name = "web"
    container.short_id = "abc123"
    container.status = "running"
    container.attrs = {"Config": {"Image": "nginx:latest"}}
    container.stats.return_value = stats_payload

    client = MagicMock()
    client.containers.list.return_value = [container]
    docker_mod = MagicMock()
    docker_mod.from_env.return_value = client
    return docker_mod, container


_STATS = {
    "cpu_stats": {
        "cpu_usage": {"total_usage": 2_000_000},
        "system_cpu_usage": 20_000_000,
        "online_cpus": 4,
    },
    "precpu_stats": {
        "cpu_usage": {"total_usage": 1_000_000},
        "system_cpu_usage": 10_000_000,
    },
    "memory_stats": {"usage": 200_000_000, "limit": 1_000_000_000, "stats": {"cache": 50_000_000}},
}


def test_container_stats_populated_when_enabled():
    docker_mod, _ = _docker_mock(_STATS)
    cfg = RavenConfig(modules=ModulesConfig(container_stats=True))
    with (
        patch("shutil.which", return_value=None),
        patch.dict("sys.modules", {"docker": docker_mod}),
    ):
        info = ContainersPlugin(cfg).collect().containers[0]

    # cpu_delta/system_delta = 1e6/1e7 = 0.1; × 4 CPUs × 100 = 40%
    assert info.cpu_percent == 40.0
    assert info.memory_usage == 150_000_000  # usage minus page cache
    assert info.memory_limit == 1_000_000_000


def test_container_stats_absent_when_disabled():
    docker_mod, container = _docker_mock(_STATS)
    cfg = RavenConfig(modules=ModulesConfig(container_stats=False))
    with (
        patch("shutil.which", return_value=None),
        patch.dict("sys.modules", {"docker": docker_mod}),
    ):
        info = ContainersPlugin(cfg).collect().containers[0]

    assert info.cpu_percent is None
    container.stats.assert_not_called()


def test_container_stats_failure_leaves_values_none():
    docker_mod, container = _docker_mock(_STATS)
    container.stats.side_effect = RuntimeError("daemon busy")
    cfg = RavenConfig(modules=ModulesConfig(container_stats=True))
    with (
        patch("shutil.which", return_value=None),
        patch.dict("sys.modules", {"docker": docker_mod}),
    ):
        info = ContainersPlugin(cfg).collect().containers[0]

    assert info.cpu_percent is None
    assert info.name == "web"  # the rest of the record still arrives


def test_container_stats_tolerates_malformed_payload():
    docker_mod, _ = _docker_mock({"cpu_stats": {}, "precpu_stats": {}, "memory_stats": {}})
    cfg = RavenConfig(modules=ModulesConfig(container_stats=True))
    with (
        patch("shutil.which", return_value=None),
        patch.dict("sys.modules", {"docker": docker_mod}),
    ):
        info = ContainersPlugin(cfg).collect().containers[0]

    assert info.cpu_percent is None
    assert info.memory_usage is None


# ── CPU frequency units ──────────────────────────────────────────────────────


def test_cpu_frequency_ghz_is_normalised_to_mhz():
    """psutil reports GHz on Apple Silicon; "4 MHz" is not a real frequency."""
    from raven.plugins.cpu import CpuPlugin

    assert CpuPlugin._normalise_mhz(4) == 4000
    assert CpuPlugin._normalise_mhz(3.5) == 3500


def test_cpu_frequency_mhz_is_left_alone():
    from raven.plugins.cpu import CpuPlugin

    assert CpuPlugin._normalise_mhz(2400.0) == 2400.0
    assert CpuPlugin._normalise_mhz(0) is None
    assert CpuPlugin._normalise_mhz(None) is None


def test_fetch_reports_untruncated_process_count(capsys, mock_config):
    """`raven fetch` printed the truncated list length, not the host total."""
    from raven.fetch import run_fetch

    run_fetch(mock_config)
    out = capsys.readouterr().out
    assert "Procs" in out


# ── A8: widget history is rendered, not collected and discarded ──────────────


def _render(widget, snapshots):
    """Drive update_data and return the Text the widget would display."""
    captured = {}
    with patch.object(type(widget), "update", lambda self, t: captured.__setitem__("t", t)):
        for snap in snapshots:
            widget.update_data(snap)
    return captured["t"].plain


def test_cpu_widget_renders_sparkline():
    from raven.core.models import CpuMetrics
    from raven.tui.widgets.cpu_widget import CpuWidget

    out = _render(
        CpuWidget(),
        [
            SystemSnapshot(cpu=CpuMetrics(percent_overall=p, percent_per_core=[p]))
            for p in (5, 90, 40)
        ],
    )
    assert "History" in out
    assert any(ch in out for ch in "▂▃▄▅▆▇█"), "sparkline blocks not rendered"


def test_memory_widget_renders_sparkline():
    from raven.core.models import MemoryMetrics
    from raven.tui.widgets.memory_widget import MemoryWidget

    out = _render(
        MemoryWidget(),
        [SystemSnapshot(memory=MemoryMetrics(total=100, used=p, percent=p)) for p in (10, 80, 50)],
    )
    assert "Trend" in out
    assert any(ch in out for ch in "▂▃▄▅▆▇█")


def test_widget_history_is_not_stored_on_the_app():
    """History used to be monkey-patched onto the App object."""
    from raven.core.models import CpuMetrics
    from raven.tui.widgets.cpu_widget import CpuWidget

    widget = CpuWidget()
    _render(widget, [SystemSnapshot(cpu=CpuMetrics(percent_overall=1.0))])
    assert len(widget._history) == 1


def test_single_sample_produces_no_sparkline():
    from raven.core.models import CpuMetrics
    from raven.tui.widgets.cpu_widget import CpuWidget

    out = _render(CpuWidget(), [SystemSnapshot(cpu=CpuMetrics(percent_overall=50.0))])
    assert "History" not in out


# ── P3-10: sensor/container widgets previously had no dedicated tests ────────


def test_sensor_widget_renders_temps_fans_battery_and_users():
    from raven.core.models import (
        BatteryInfo,
        FanReading,
        SensorMetrics,
        TemperatureReading,
        UserInfo,
    )
    from raven.tui.widgets.sensor_widget import SensorWidget

    snap = SystemSnapshot(
        sensors=SensorMetrics(
            temperatures=[TemperatureReading(label="Core 0", current=55.0, high=90.0)],
            fans=[FanReading(label="Fan 1", current=2200)],
            battery=BatteryInfo(percent=42.0, power_plugged=False),
        ),
        users=[UserInfo(name="alice"), UserInfo(name="bob")],
    )
    out = _render(SensorWidget(), [snap])
    assert "Temps" in out and "Core 0" in out and "55" in out
    assert "Fans" in out and "2200 RPM" in out
    assert "Battery" in out and "42%" in out and "🔋" in out
    assert "Users" in out and "alice" in out and "bob" in out


def test_sensor_widget_reports_no_data_when_all_empty():
    from raven.tui.widgets.sensor_widget import SensorWidget

    out = _render(SensorWidget(), [SystemSnapshot()])
    assert "No sensor data" in out


def test_container_widget_hides_panel_when_no_runtime_available():
    from raven.tui.widgets.container_widget import ContainerWidget

    widget = ContainerWidget()
    widget.update_data(SystemSnapshot())  # docker_available=False, lxc_available=False
    assert widget.display is False


def test_container_widget_shows_running_containers():
    from raven.core.models import ContainerInfo, ContainerMetrics
    from raven.tui.widgets.container_widget import ContainerWidget

    snap = SystemSnapshot(
        containers=ContainerMetrics(
            containers=[
                ContainerInfo(name="web", image="nginx", status="running", runtime="docker"),
                ContainerInfo(name="db", image="postgres", status="exited", runtime="docker"),
            ],
            docker_available=True,
        )
    )
    out = _render(ContainerWidget(), [snap])
    assert "Containers" in out
    assert "1/2 running" in out
    assert "web" in out and "nginx" in out
    assert "db" in out and "postgres" in out


def test_container_widget_reports_empty_state_when_runtime_available_but_idle():
    from raven.core.models import ContainerMetrics
    from raven.tui.widgets.container_widget import ContainerWidget

    snap = SystemSnapshot(containers=ContainerMetrics(containers=[], docker_available=True))
    out = _render(ContainerWidget(), [snap])
    assert "No containers detected" in out


# ── A6: plugins share a uniform constructor ──────────────────────────────────


def test_every_builtin_plugin_accepts_config():
    """get_enabled_plugins no longer inspects signatures to decide how to build."""
    import importlib

    from raven.core.plugin_manager import _BUILTIN_PLUGINS, _load_plugin_module

    for mod_name in _BUILTIN_PLUGINS:
        importlib.import_module(f"raven.plugins.{mod_name}")
        cls = _load_plugin_module(mod_name)
        assert cls is not None, mod_name
        assert cls(config=RavenConfig()) is not None, mod_name


# ── M8: the no-op --once flag is gone ────────────────────────────────────────


def test_once_flag_removed():
    from raven.cli import _build_parser

    with pytest.raises(SystemExit):
        _build_parser().parse_args(["print", "--once"])
