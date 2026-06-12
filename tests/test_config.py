import os
import tempfile

import pytest

from raven.config import (
    ExportConfig,
    GeneralConfig,
    ProcessesConfig,
    RavenConfig,
    RemoteConfig,
    WebConfig,
    _dict_to_config,
    load_config,
    validate_config,
)


def test_default_config():
    cfg = load_config()
    assert isinstance(cfg, RavenConfig)
    assert cfg.general.refresh_interval == 2.0
    assert cfg.web.host == "127.0.0.1"
    assert cfg.remote.host == "127.0.0.1"


def test_dict_to_config_filtering():
    raw_data = {
        "general": {"refresh_interval": 5.0, "unknown_key": "ignored"},
        "modules": {"cpu": True},
        "web": {"port": 9999, "invalid": 123},
    }
    cfg = _dict_to_config(raw_data)
    assert cfg.general.refresh_interval == 5.0
    assert cfg.web.port == 9999


def test_load_explicit_config():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("[general]\nrefresh_interval = 10.0\n[web]\nenabled = true\nport = 8888\n")
        f_path = f.name

    try:
        cfg = load_config(explicit_path=f_path)
        assert cfg.general.refresh_interval == 10.0
        assert cfg.web.enabled is True
        assert cfg.web.port == 8888
    finally:
        os.unlink(f_path)


def test_config_validation():
    # Valid config
    valid_cfg = RavenConfig()
    validate_config(valid_cfg)  # should not raise

    # Invalid refresh_interval
    with pytest.raises(ValueError, match="refresh_interval must be >= 1"):
        validate_config(RavenConfig(general=GeneralConfig(refresh_interval=0)))

    # Invalid theme
    with pytest.raises(ValueError, match="theme must be 'dark' or 'light'"):
        validate_config(RavenConfig(general=GeneralConfig(theme="blue")))

    # Invalid web port
    with pytest.raises(ValueError, match="web.port must be between 1 and 65535"):
        validate_config(RavenConfig(web=WebConfig(port=99999)))

    # Invalid remote port
    with pytest.raises(ValueError, match="remote.port must be between 1 and 65535"):
        validate_config(RavenConfig(remote=RemoteConfig(port=0)))

    # Invalid format
    with pytest.raises(ValueError, match="export.format must be 'text', 'csv', or 'json'"):
        validate_config(RavenConfig(export=ExportConfig(format="yaml")))

    # Invalid max_display
    with pytest.raises(ValueError, match="processes.max_display must be >= 1"):
        validate_config(RavenConfig(processes=ProcessesConfig(max_display=0)))

    # Invalid sort_by
    with pytest.raises(ValueError, match="processes.sort_by must be one of"):
        validate_config(RavenConfig(processes=ProcessesConfig(sort_by="invalid")))

