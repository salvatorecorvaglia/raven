import pytest

from raven.core.collector import Collector
from raven.core.models import SystemSnapshot


def test_collector_initialization(mock_config):
    collector = Collector(mock_config)
    assert len(collector.plugins) > 0
    assert collector.config == mock_config

def test_collector_collect(mock_config):
    collector = Collector(mock_config)
    # Perform a real collection run on the local machine
    snapshot = collector.collect()
    assert isinstance(snapshot, SystemSnapshot)
    assert snapshot.timestamp > 0
    assert snapshot.system_info is not None

@pytest.mark.asyncio
async def test_collector_collect_async(mock_config):
    collector = Collector(mock_config)
    snapshot = await collector.collect_async()
    assert isinstance(snapshot, SystemSnapshot)
    assert snapshot.timestamp > 0
