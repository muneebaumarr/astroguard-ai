import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.repositories.memory import MemoryAdapterFactory
from astroguard_contracts import dto as d
from astroguard_contracts.fixtures import ASTRONAUT_IDS, MISSION_ID, representative_fixtures, stable_id


@pytest.fixture
def client():
    with TestClient(create_app(Settings())) as client:
        yield client


@pytest.mark.parametrize("path,model", [
    ("health", d.HealthResponse), ("ready", d.ReadinessResult),
    ("missions", d.Page[d.Mission]), (f"missions/{MISSION_ID}", d.Mission),
    ("astronauts", d.Page[d.Astronaut]), (f"astronauts/{ASTRONAUT_IDS[0]}", d.Astronaut),
])
def test_read_endpoints(client, path, model):
    response = client.get(f"/api/v1/{path}")
    assert response.status_code == 200
    assert model.model_validate(response.json())
    assert response.headers["x-request-id"]


def test_exact_fictional_profiles_and_pagination(client):
    fixtures = representative_fixtures()
    profiles = client.get("/api/v1/astronauts").json()
    assert profiles["items"] == [r.model_dump(mode="json") for r in sorted(fixtures["astronauts"], key=lambda r: r.id)]
    page = client.get("/api/v1/astronauts?limit=1&offset=1").json()
    assert page["total"] == 2 and len(page["items"]) == 1
    assert page["items"][0] == profiles["items"][1]
    filtered = client.get(f"/api/v1/astronauts?mission_id={stable_id('missing')}").json()
    assert filtered["items"] == [] and filtered["total"] == 0


@pytest.mark.parametrize("path", [f"astronauts/{stable_id('missing')}", f"missions/{stable_id('missing')}", "not-an-endpoint"])
def test_not_found_envelope(client, path):
    response = client.get(f"/api/v1/{path}")
    assert response.status_code == 404
    parsed = d.ErrorResponse.model_validate(response.json())
    assert parsed.error.code == "not_found"
    assert parsed.error.request_id == response.headers["x-request-id"]


@pytest.mark.parametrize("path", ["astronauts/not-a-uuid", "missions/invalid", "astronauts?limit=0", "missions?offset=-1", "astronauts?mission_id=invalid", "astronauts?limit=1001"])
def test_validation_envelope(client, path):
    response = client.get(f"/api/v1/{path}")
    assert response.status_code == 422
    error = d.ErrorResponse.model_validate(response.json()).error
    assert error.code == "validation_error" and error.details


def test_ready_unavailable_and_clean_shutdown():
    adapter = MemoryAdapterFactory()
    with TestClient(create_app(Settings(), adapter)) as client:
        adapter.close()
        response = client.get("/api/v1/ready")
        assert response.status_code == 503
        assert d.ReadinessResult.model_validate(response.json()).ready is False
        assert client.get("/api/v1/astronauts").status_code == 503


def test_config_never_falls_back_to_memory():
    with pytest.raises(RuntimeError, match="no memory fallback"):
        create_app(Settings(repository_backend="sqlite"))


def test_configuration_from_environment(monkeypatch):
    monkeypatch.setenv("REPOSITORY_BACKEND", "sqlite")
    monkeypatch.setenv("CORS_ORIGINS", "http://127.0.0.1:5173, http://localhost:5173")
    settings = Settings.from_env()
    assert settings.repository_backend == "sqlite"
    assert settings.cors_origins == ("http://127.0.0.1:5173", "http://localhost:5173")


def test_cors(client):
    response = client.options("/api/v1/astronauts", headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "GET"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    denied = client.get("/api/v1/health", headers={"Origin": "https://unconfigured.invalid"})
    assert "access-control-allow-origin" not in denied.headers


def test_existing_endpoints_and_get_side_effects_remain_unchanged(client):
    adapter = client.app.state.adapter
    before = {name: len(records) for name, records in adapter._state.items()}
    for _ in range(3):
        client.get("/api/v1/astronauts")
        client.get("/api/v1/missions")
    assert before == {name: len(records) for name, records in adapter._state.items()}
    paths = set(client.get("/openapi.json").json()["paths"])
    assert paths == {"/api/v1/health", "/api/v1/ready", "/api/v1/missions", "/api/v1/missions/{id}", "/api/v1/astronauts", "/api/v1/astronauts/{id}",
        "/api/v1/astronauts/{id}/checkins", "/api/v1/astronauts/{id}/checkins/{checkin_id}",
        "/api/v1/astronauts/{id}/readings", "/api/v1/astronauts/{id}/assessments",
        "/api/v1/astronauts/{id}/assessments/{assessment_id}",
        "/api/v1/astronauts/{id}/alerts", "/api/v1/astronauts/{id}/alerts/{alert_id}/acknowledgement",
        "/api/v1/simulation/scenarios", "/api/v1/simulation/runs", "/api/v1/simulation/runs/{id}",
        "/api/v1/simulation/runs/{id}/steps", "/api/v1/simulation/runs/{id}/pause",
        "/api/v1/simulation/runs/{id}/resume", "/api/v1/simulation/runs/{id}/stop",
        "/api/v1/astronauts/{id}/telemetry/latest", "/api/v1/missions/{id}/telemetry/latest",
        "/api/v1/missions/{id}/environmental-readings"}
    assert client.post(f"/api/v1/astronauts/{ASTRONAUT_IDS[0]}/checkins", json={}).status_code == 422


def test_empty_repository():
    with TestClient(create_app(Settings(), MemoryAdapterFactory(fixtures={}))) as client:
        assert client.get("/api/v1/astronauts").json()["items"] == []
        assert client.get("/api/v1/missions").json()["items"] == []


def test_application_restart_resets_memory():
    app = create_app(Settings())
    with TestClient(app) as client:
        first_adapter = client.app.state.adapter
        with first_adapter.create_uow() as uow:
            fixture = representative_fixtures()["missions"][0]
            uow.missions.add(d.Mission.model_validate(fixture.model_dump() | {"id": stable_id("temporary")}))
            uow.commit()
        assert client.get("/api/v1/missions").json()["total"] == 2
    assert first_adapter.check_ready().ready is False
    with TestClient(app) as client:
        assert client.get("/api/v1/missions").json()["total"] == 1
