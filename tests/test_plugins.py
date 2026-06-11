from unittest.mock import MagicMock, patch

from raven.plugins.cpu import CpuPlugin
from raven.plugins.disk import DiskPlugin
from raven.plugins.memory import MemoryPlugin
from raven.plugins.network import NetworkPlugin
from raven.plugins.processes import ProcessesPlugin
from raven.plugins.sensors import SensorsPlugin
from raven.plugins.system_info import SystemInfoPlugin
from raven.plugins.users import UsersPlugin


@patch("psutil.cpu_percent")
@patch("psutil.cpu_count")
@patch("psutil.cpu_freq", create=True)
@patch("psutil.getloadavg", create=True)
def test_cpu_plugin(mock_loadavg, mock_freq, mock_count, mock_percent):
    mock_percent.return_value = 15.0
    mock_count.return_value = 4
    mock_freq.return_value = MagicMock(current=2500.0, max=3000.0)
    mock_loadavg.return_value = (1.0, 1.0, 1.0)

    plugin = CpuPlugin()
    assert plugin.is_available() is True
    metrics = plugin.collect()
    assert metrics.percent_overall == 15.0
    assert metrics.core_count_logical == 4


@patch("psutil.virtual_memory")
@patch("psutil.swap_memory")
def test_memory_plugin(mock_swap, mock_virtual):
    mock_virtual.return_value = MagicMock(total=8000, available=4000, used=4000, percent=50.0)
    mock_swap.return_value = MagicMock(total=2000, used=1000, percent=50.0)

    plugin = MemoryPlugin()
    assert plugin.is_available() is True
    metrics = plugin.collect()
    assert metrics.total == 8000
    assert metrics.percent == 50.0
    assert metrics.swap_total == 2000


@patch("psutil.disk_partitions")
@patch("psutil.disk_usage")
@patch("psutil.disk_io_counters")
def test_disk_plugin(mock_io, mock_usage, mock_partitions):
    mock_partitions.return_value = [
        MagicMock(device="/dev/sda1", mountpoint="/", fstype="ext4", opts="rw")
    ]
    mock_usage.return_value = MagicMock(total=1000, used=500, free=500, percent=50.0)
    mock_io.return_value = MagicMock(
        read_count=10,
        write_count=20,
        read_bytes=100,
        write_bytes=200,
        read_time=1,
        write_time=2,
    )

    plugin = DiskPlugin()
    assert plugin.is_available() is True
    metrics = plugin.collect()
    assert len(metrics.partitions) == 1
    assert metrics.partitions[0].mountpoint == "/"
    assert metrics.io.read_bytes == 100


@patch("psutil.net_io_counters")
@patch("psutil.net_if_addrs")
@patch("psutil.net_connections")
def test_network_plugin(mock_conns, mock_addrs, mock_io):
    mock_io.return_value = {
        "eth0": MagicMock(
            bytes_sent=1000,
            bytes_recv=2000,
            packets_sent=10,
            packets_recv=20,
            errin=0,
            errout=0,
            dropin=0,
            dropout=0,
        )
    }
    mock_addrs.return_value = {}
    mock_conns.return_value = [1, 2, 3]

    plugin = NetworkPlugin()
    assert plugin.is_available() is True
    metrics = plugin.collect()
    assert len(metrics.interfaces) == 1
    assert metrics.interfaces[0].name == "eth0"
    assert metrics.connections_count == 3


@patch("psutil.process_iter")
def test_processes_plugin(mock_proc_iter):
    # Mocking two raw processes
    proc1 = MagicMock()
    proc1.pid = 1
    proc1.cpu_percent.return_value = 10.0
    proc1.memory_percent.return_value = 5.0
    proc1.info = {"pid": 1, "cpu_percent": 10.0, "memory_percent": 5.0}
    proc1.as_dict.return_value = {
        "name": "proc1",
        "username": "user1",
        "status": "running",
        "cmdline": ["proc1", "arg"],
        "num_threads": 2,
        "memory_info": MagicMock(rss=5000),
    }

    mock_proc_iter.return_value = [proc1]

    plugin = ProcessesPlugin()
    assert plugin.is_available() is True
    metrics = plugin.collect()
    assert len(metrics) == 1
    assert metrics[0].pid == 1
    assert metrics[0].name == "proc1"
    assert metrics[0].cpu_percent == 10.0


@patch("platform.node")
@patch("platform.system")
@patch("platform.release")
@patch("platform.machine")
@patch("psutil.boot_time")
def test_system_info_plugin(mock_boot, mock_mach, mock_rel, mock_sys, mock_node):
    mock_node.return_value = "host1"
    mock_sys.return_value = "Linux"
    mock_rel.return_value = "5.0"
    mock_mach.return_value = "x86_64"
    mock_boot.return_value = 1000.0

    plugin = SystemInfoPlugin()
    assert plugin.is_available() is True
    metrics = plugin.collect()
    assert metrics.hostname == "host1"
    assert metrics.os_name == "Linux"


@patch("psutil.users")
def test_users_plugin(mock_users):
    user = MagicMock()
    user.name = "user1"
    user.terminal = "pts/1"
    user.host = "localhost"
    user.started = 100.0
    user.pid = 123
    mock_users.return_value = [user]

    plugin = UsersPlugin()
    assert plugin.is_available() is True
    metrics = plugin.collect()
    assert len(metrics) == 1
    assert metrics[0].name == "user1"


@patch("psutil.sensors_temperatures", create=True)
@patch("psutil.sensors_fans", create=True)
@patch("psutil.sensors_battery", create=True)
def test_sensors_plugin(mock_bat, mock_fans, mock_temps):
    mock_temps.return_value = {
        "cpu_thermal": [MagicMock(label="Core 0", current=45.0, high=80.0, critical=90.0)]
    }
    mock_fans.return_value = {"fan1": [MagicMock(label="Fan 1", current=2000)]}
    mock_bat.return_value = MagicMock(percent=95.0, secsleft=-1, power_plugged=True)

    plugin = SensorsPlugin()
    assert plugin.is_available() is True
    metrics = plugin.collect()
    assert len(metrics.temperatures) == 1
    assert metrics.temperatures[0].label == "Core 0"
    assert metrics.battery.percent == 95.0
    assert metrics.battery.secs_left is None


@patch("psutil.process_iter")
def test_processes_plugin_caching(mock_proc_iter):
    proc = MagicMock()
    proc.pid = 42
    proc.cpu_percent.return_value = 25.0
    proc.memory_percent.return_value = 12.0
    proc.info = {"pid": 42, "cpu_percent": 25.0, "memory_percent": 12.0}
    proc.as_dict.return_value = {
        "name": "cached_proc",
        "username": "user",
        "status": "running",
        "cmdline": ["run"],
        "num_threads": 4,
        "memory_info": MagicMock(rss=8000),
    }

    mock_proc_iter.return_value = [proc]

    plugin = ProcessesPlugin()
    assert len(plugin._proc_cache) == 0

    # First collect: populates cache
    metrics1 = plugin.collect()
    assert len(metrics1) == 1
    assert metrics1[0].pid == 42
    assert len(plugin._proc_cache) == 1
    assert plugin._proc_cache[42] is proc
    proc.cpu_percent.assert_called_with(interval=None)

    # Second collect: process continues using cache
    metrics2 = plugin.collect()
    assert len(metrics2) == 1
    assert metrics2[0].pid == 42
    assert len(plugin._proc_cache) == 1

    # Third collect: process disappears, cache should be cleared
    mock_proc_iter.return_value = []
    metrics3 = plugin.collect()
    assert len(metrics3) == 0
    assert len(plugin._proc_cache) == 0
