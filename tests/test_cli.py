import argparse
import pytest

from raven.cli import remote_address_type


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
