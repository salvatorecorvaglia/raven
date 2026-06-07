import os
import tempfile

from raven.config import RavenConfig, _dict_to_config, load_config


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
