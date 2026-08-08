from unittest.mock import MagicMock, patch

from raven.plugins.containers import ContainersPlugin


def test_containers_plugin_always_loadable():
    """The plugin stays loaded even with no runtime present.

    Availability is re-checked per collect() and reported through the metrics,
    so a Docker daemon started after Raven does not require a restart.
    """
    with patch("shutil.which", return_value=None), patch.dict("sys.modules", {"docker": None}):
        plugin = ContainersPlugin()
        assert plugin.is_available() is True
        metrics = plugin.collect()
        assert metrics.docker_available is False
        assert metrics.lxc_available is False
        assert metrics.containers == []


def test_containers_plugin_detects_docker_started_later():
    """A daemon that appears after startup is picked up without a restart."""
    mock_docker = MagicMock()
    mock_client = MagicMock()
    mock_client.containers.list.return_value = []
    mock_docker.from_env.return_value = mock_client

    with patch("shutil.which", return_value=None), patch.dict("sys.modules", {"docker": None}):
        plugin = ContainersPlugin()
        assert plugin.collect().docker_available is False

    # Docker comes up; expire the 30 s availability cache to force a re-check.
    with (
        patch("shutil.which", return_value=None),
        patch.dict("sys.modules", {"docker": mock_docker}),
    ):
        plugin._last_check = 0.0
        assert plugin.collect().docker_available is True


def test_containers_plugin_docker_only():
    mock_docker = MagicMock()
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_container.name = "my-docker-container"
    mock_container.short_id = "abc123def"
    mock_container.status = "running"
    mock_container.attrs = {"Config": {"Image": "nginx:latest"}}

    mock_client.containers.list.return_value = [mock_container]
    mock_docker.from_env.return_value = mock_client

    with (
        patch("shutil.which", return_value=None),
        patch.dict("sys.modules", {"docker": mock_docker}),
    ):
        plugin = ContainersPlugin()
        metrics = plugin.collect()
        assert plugin._docker_ok is True
        assert plugin._lxc_ok is False

        assert metrics.docker_available is True
        assert metrics.lxc_available is False
        assert len(metrics.containers) == 1
        assert metrics.containers[0].name == "my-docker-container"
        assert metrics.containers[0].container_id == "abc123def"
        assert metrics.containers[0].image == "nginx:latest"
        assert metrics.containers[0].status == "running"
        assert metrics.containers[0].runtime == "docker"


def test_containers_plugin_lxc_only():
    mock_lxc_list_json = """[
        {
            "name": "my-lxc-container",
            "status": "Running",
            "config": {
                "image.description": "ubuntu 22.04"
            }
        }
    ]"""
    mock_process = MagicMock()
    mock_process.communicate.return_value = (mock_lxc_list_json, "")
    mock_process.stdout.read.return_value = mock_lxc_list_json
    mock_process.wait.return_value = None
    mock_process.returncode = 0

    with (
        patch("shutil.which", return_value="/usr/bin/lxc"),
        patch("subprocess.Popen", return_value=mock_process),
        patch.dict("sys.modules", {"docker": None}),
    ):
        plugin = ContainersPlugin()
        metrics = plugin.collect()
        assert plugin._docker_ok is False
        assert plugin._lxc_ok is True

        assert metrics.docker_available is False
        assert metrics.lxc_available is True
        assert len(metrics.containers) == 1
        assert metrics.containers[0].name == "my-lxc-container"
        assert metrics.containers[0].container_id == "my-lxc-container"
        assert metrics.containers[0].image == "ubuntu 22.04"
        assert metrics.containers[0].status == "running"
        assert metrics.containers[0].runtime == "lxc"


def test_containers_plugin_docker_timeout():
    mock_docker = MagicMock()
    mock_client = MagicMock()
    mock_client.ping.side_effect = Exception("Connection timed out")
    mock_docker.from_env.return_value = mock_client

    with (
        patch("shutil.which", return_value=None),
        patch.dict("sys.modules", {"docker": mock_docker}),
    ):
        plugin = ContainersPlugin()
        metrics = plugin.collect()
        assert metrics.docker_available is False
        assert plugin._docker_ok is False
        mock_docker.from_env.assert_called_with(timeout=5)
