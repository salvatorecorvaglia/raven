import pytest
from fastapi.testclient import TestClient

from raven.config import RavenConfig, WebConfig
from raven.core.collector import Collector
from raven.web.server import create_app


@pytest.fixture
def api_client(mock_config):
    # Set up config with a mock API key
    cfg = RavenConfig(
        web=WebConfig(api_key="secret-key", host="127.0.0.1", port=8080)
    )
    app = create_app(cfg)
    return TestClient(app)


def test_api_health_check(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_static_skip_auth(api_client):
    response = api_client.get("/")
    assert response.status_code == 200
    assert "Raven" in response.text


def test_api_auth_required_without_key(api_client):
    response = api_client.get("/api/v1/snapshot")
    assert response.status_code == 401
    assert "Missing API key" in response.json()["detail"]


def test_api_auth_required_invalid_key(api_client):
    response = api_client.get("/api/v1/snapshot", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401
    assert "Invalid API key" in response.json()["detail"]


def test_api_auth_success(api_client):
    response = api_client.get("/api/v1/snapshot", headers={"X-API-Key": "secret-key"})
    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    assert "cpu" in data


def test_api_module_endpoint(api_client):
    # Valid module
    response = api_client.get("/api/v1/cpu", headers={"X-API-Key": "secret-key"})
    assert response.status_code == 200
    res = response.json()
    assert res["module"] == "cpu"
    assert "percent_overall" in res["data"]

    # Invalid module
    response = api_client.get("/api/v1/invalid_module", headers={"X-API-Key": "secret-key"})
    assert response.status_code == 404
    assert "Unknown module" in response.json()["detail"]


def test_api_static_files(api_client):
    response = api_client.get("/static/style.css")
    assert response.status_code == 200
    assert "body" in response.text
