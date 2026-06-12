import argparse
from unittest.mock import patch

import pytest

from raven.cli import main, remote_address_type


def test_remote_address_validation_valid():
    assert remote_address_type("localhost:8080") == "localhost:8080"
    assert remote_address_type("192.168.1.10:9090") == "192.168.1.10:9090"
    assert remote_address_type("http://myagent:80") == "http://myagent:80"
    assert remote_address_type("https://myagent:443") == "https://myagent:443"


def test_remote_address_validation_invalid():
    # Empty hostname or missing host
    with pytest.raises(argparse.ArgumentTypeError, match="Invalid remote address format"):
        remote_address_type(":8080")

    # Invalid port bounds
    with pytest.raises(argparse.ArgumentTypeError, match="Invalid remote address format"):
        remote_address_type("localhost:999999")

    with pytest.raises(argparse.ArgumentTypeError, match="Invalid remote address format"):
        remote_address_type("localhost:0")


def test_cli_subcommands_routing():
    with patch("raven.cli._cmd_tui") as mock_tui:
        main([])
        mock_tui.assert_called_once()

    with patch("raven.fetch.run_fetch") as mock_fetch:
        main(["fetch"])
        mock_fetch.assert_called_once()

    with patch("raven.cli._cmd_print") as mock_print:
        main(["print", "cpu", "-f", "json"])
        mock_print.assert_called_once()

    with patch("raven.cli._cmd_web") as mock_web:
        main(["web", "--host", "127.0.0.1", "-p", "8080"])
        mock_web.assert_called_once()

    with patch("raven.cli._cmd_serve") as mock_serve:
        main(["serve", "--host", "0.0.0.0", "-p", "9090"])
        mock_serve.assert_called_once()
