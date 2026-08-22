import pytest

from raven.tui.app import RavenApp


@pytest.mark.asyncio
async def test_tui_app_mount(mock_config, mock_collector):
    app = RavenApp(collector=mock_collector, config=mock_config)
    async with app.run_test():
        assert app.title == "🐦‍⬛ Raven System Monitor"
        # Verify that all panel widgets exist
        assert app.query_one("#cpu-panel") is not None
        assert app.query_one("#memory-panel") is not None
        assert app.query_one("#process-panel") is not None
        assert app.query_one("#disk-panel") is not None
        assert app.query_one("#network-panel") is not None
        assert app.query_one("#sensor-panel") is not None
        assert app.query_one("#container-panel") is not None


@pytest.mark.asyncio
async def test_process_table_updates(mock_config, dummy_snapshot, make_collector):
    from raven.core.models import ProcessInfo, SystemSnapshot
    from raven.tui.widgets.process_table import ProcessTable

    snap = SystemSnapshot(
        timestamp=dummy_snapshot.timestamp,
        processes=[ProcessInfo(pid=1, name="init", cpu_percent=1.0, memory_percent=0.5)],
    )

    app = RavenApp(collector=make_collector(snap), config=mock_config)
    async with app.run_test():
        table = app.query_one("#process-panel", ProcessTable)
        assert table is not None
        table.update_data(snap, max_display=10, sort_by="cpu")
        assert table.row_count > 0


@pytest.mark.asyncio
async def test_reconcile_process_sort_uses_collector_override(mock_config, dummy_snapshot):
    """Cycling to a non-default sort must re-collect via collect_processes_async
    (when the collector supports it) rather than only re-sorting the snapshot
    the plugin already truncated by the configured default sort key."""
    from raven.core.models import ProcessInfo

    fresh_procs = [ProcessInfo(pid=42, name="reconciled", cpu_percent=1.0, memory_percent=99.0)]

    class StubCollector:
        async def collect_async(self):
            return dummy_snapshot

        async def collect_processes_async(self, sort_by):
            assert sort_by == "memory"
            return fresh_procs

        def close(self):
            pass

        async def close_async(self):
            pass

    assert mock_config.processes.sort_by == "cpu"
    app = RavenApp(collector=StubCollector(), config=mock_config)
    app._sort_index = 1  # "memory" in _SORT_CYCLE

    reconciled = await app._reconcile_process_sort(dummy_snapshot)
    assert reconciled.processes == fresh_procs


@pytest.mark.asyncio
async def test_reconcile_process_sort_is_noop_on_configured_default_sort(
    mock_config, dummy_snapshot, mock_collector
):
    """No override call when the active sort already matches the plugin's
    truncation key — MockMetricCollector doesn't even implement
    collect_processes_async, so this also covers collectors that can't."""
    app = RavenApp(collector=mock_collector, config=mock_config)
    reconciled = await app._reconcile_process_sort(dummy_snapshot)
    assert reconciled is dummy_snapshot
