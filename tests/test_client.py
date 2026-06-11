import dataclasses

from raven.core.models import SystemSnapshot
from raven.remote.client import RemoteCollector


def test_client_parse_roundtrip(dummy_snapshot):
    # Serialize snapshot to dict (as if coming from the remote API)
    serialized = dataclasses.asdict(dummy_snapshot)

    # Introduce an unexpected extra key to test BUG-5 resolution/resilience
    serialized["sensors"]["temperatures"].append(
        {
            "label": "ExtraTemp",
            "current": 42.0,
            "high": 80.0,
            "critical": 90.0,
            "future_field": "some-value",  # Unexpected key
        }
    )

    # Add a mock remote collector instance
    client = RemoteCollector(address="http://localhost:9090", api_key="")

    # Parse it back
    parsed = client._parse(serialized)

    # Verify parsed types
    assert isinstance(parsed, SystemSnapshot)
    assert parsed.system_info.hostname == "test-host"
    assert len(parsed.sensors.temperatures) == 1
    assert parsed.sensors.temperatures[0].label == "ExtraTemp"
    assert parsed.sensors.temperatures[0].current == 42.0


def test_client_parse_robustness():
    # Test with partial keys and null values
    partial_data = {
        "timestamp": 12345.0,
        "cpu": None,
        "memory": None,
        "disk": None,
        "network": None,
        "system_info": None,
        "sensors": None,
        "containers": None,
        "users": None,
        "processes": None,
    }
    client = RemoteCollector(address="http://localhost:9090", api_key="")
    parsed = client._parse(partial_data)

    assert isinstance(parsed, SystemSnapshot)
    assert parsed.timestamp == 12345.0
    assert parsed.cpu.percent_overall == 0.0
    assert parsed.memory.total == 0
    assert parsed.disk.partitions == []
    assert parsed.network.interfaces == []
    assert parsed.processes == []
    assert parsed.users == []
    assert parsed.sensors.temperatures == []
    assert parsed.containers.containers == []
