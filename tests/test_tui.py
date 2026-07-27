import pytest

from raven.tui.app import RavenApp


class MockMetricCollector:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    async def collect_async(self):
        return self.snapshot

    def close(self):
        pass

    async def close_async(self):
        pass


@pytest.mark.asyncio
async def test_tui_app_mount(mock_config, dummy_snapshot):
    collector = MockMetricCollector(dummy_snapshot)
    app = RavenApp(collector=collector, config=mock_config)
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
async def test_process_table_updates(mock_config, dummy_snapshot):
    from raven.core.models import ProcessInfo, SystemSnapshot
    from raven.tui.widgets.process_table import ProcessTable

    snap = SystemSnapshot(
        timestamp=dummy_snapshot.timestamp,
        processes=[ProcessInfo(pid=1, name="init", cpu_percent=1.0, memory_percent=0.5)],
    )

    collector = MockMetricCollector(snap)
    app = RavenApp(collector=collector, config=mock_config)
    async with app.run_test():
        table = app.query_one("#process-panel", ProcessTable)
        assert table is not None
        table.update_data(snap, max_display=10, sort_by="cpu")
        assert table.row_count > 0
