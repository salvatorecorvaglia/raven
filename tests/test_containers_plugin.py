from unittest.mock import MagicMock, patch

from raven.plugins.containers import ContainersPlugin


def test_containers_plugin_unavailable():
    with patch("shutil.which", return_value=None), patch.dict("sys.modules", {"docker": None}):
        plugin = ContainersPlugin()
        assert plugin.is_available() is False
        metrics = plugin.collect()
        assert metrics.docker_available is False
        assert metrics.lxc_available is False
        assert metrics.containers == []


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
        assert plugin.is_available() is True
        assert plugin._docker_ok is True
        assert plugin._lxc_ok is False

        metrics = plugin.collect()
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
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = mock_lxc_list_json

    with (
        patch("shutil.which", return_value="/usr/bin/lxc"),
        patch("subprocess.run", return_value=mock_result),
        patch.dict("sys.modules", {"docker": None}),
    ):
        plugin = ContainersPlugin()
        assert plugin.is_available() is True
        assert plugin._docker_ok is False
        assert plugin._lxc_ok is True

        metrics = plugin.collect()
        assert metrics.docker_available is False
        assert metrics.lxc_available is True
        assert len(metrics.containers) == 1
        assert metrics.containers[0].name == "my-lxc-container"
        assert metrics.containers[0].container_id == "my-lxc-container"
        assert metrics.containers[0].image == "ubuntu 22.04"
        assert metrics.containers[0].status == "running"
        assert metrics.containers[0].runtime == "lxc"
