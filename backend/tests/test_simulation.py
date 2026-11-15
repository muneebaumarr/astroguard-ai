from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.repositories.memory import MemoryAdapterFactory
from app.repositories.memory.adapter import EnvironmentalReadingRepository, SimulationRunRepository, CommandReceiptRepository, MemoryUnitOfWork
from app.services.simulation import SimulationService
from app.simulation.generator import generate_tick, VERSION
from astroguard_contracts import dto as d
from astroguard_contracts.enums import Scenario
from astroguard_contracts.errors import RepositoryUnavailable
from astroguard_contracts.fixtures import ASTRONAUT_IDS, MISSION_ID, representative_fixtures, stable_id

BODY = {"astronaut_id": ASTRONAUT_IDS[0], "scenario": "routine", "seed": 42,
        "simulation_start_at": "2026-11-15T12:00:00Z"}
BASE = "/api/v1/simulation/runs"


@pytest.fixture
def adapter():
    return MemoryAdapterFactory({k: v for k, v in representative_fixtures().items() if k in ("missions", "astronauts")})


@pytest.fixture
def client(adapter):
    with TestClient(create_app(Settings(), adapter), raise_server_exceptions=False) as client:
        yield client


def post(client, path=BASE, body=BODY, key=None):
    return client.post(path, json=body, headers={"Idempotency-Key": key or str(uuid4())})


def step(client, run, steps=1, key=None):
    return post(client, f"{BASE}/{run['id']}/steps", {"steps": steps}, key)


def values(records):
    return [(r.indicator, r.value, r.unit, r.observed_at) for r in records]


@pytest.mark.parametrize("scenario", list(Scenario))
def test_each_scenario_is_valid_and_deterministic(client, scenario):
    run = d.SimulationRun.model_validate(post(client, body=BODY | {"scenario": scenario}).json())
    now = datetime.now(timezone.utc)
    first = generate_tick(run, 2, now)
    second = generate_tick(run, 2, now)
    assert first == second
    other_id = d.SimulationRun.model_validate(run.model_dump() | {"id": stable_id("another-run")})
    other_seed = d.SimulationRun.model_validate(run.model_dump() | {"seed": 43})
    assert values(first[0]) == values(generate_tick(other_id, 2, now)[0])
    assert values(first[0]) != values(generate_tick(other_seed, 2, now)[0])
    assert all(r.source == "simulated" and r.is_demo for records in first for r in records)


def test_create_steps_association_and_retrieval(client, adapter):
    response = post(client)
    assert response.status_code == 201
    run = response.json()
    assert run["status"] == "paused" and run["last_tick_index"] == -1
    assert adapter._state["health_readings"] == adapter._state["environmental_readings"] == {}
    result = step(client, run, 2)
    assert result.status_code == 200, result.text
    parsed = d.SimulationStepResult.model_validate(result.json())
    assert parsed.run.last_tick_index == 1
    assert parsed.generated_health_count == 6 and parsed.generated_environmental_count == 4
    health = client.get(f"/api/v1/astronauts/{ASTRONAUT_IDS[0]}/readings", params={"simulation_run_id": run["id"]}).json()
    assert health["total"] == 6
    assert {r["astronaut_id"] for r in health["items"]} == {ASTRONAUT_IDS[0]}
    assert {r["unit"] for r in health["items"]} == {"bpm", "%", "degC"}
    assert {r["observed_at"] for r in health["items"]} == {"2026-11-15T12:00:00Z", "2026-11-15T12:01:00Z"}
    environment = client.get(f"/api/v1/missions/{MISSION_ID}/environmental-readings", params={"simulation_run_id": run["id"]}).json()
    assert environment["total"] == 4
    assert {r["mission_id"] for r in environment["items"]} == {MISSION_ID}
    assert {r["unit"] for r in environment["items"]} == {"ppm", "uSv/h"}
    assert client.get(f"/api/v1/astronauts/{ASTRONAUT_IDS[1]}/readings", params={"simulation_run_id": run["id"]}).json()["items"] == []
    latest = d.HealthTelemetry.model_validate(client.get(f"/api/v1/astronauts/{ASTRONAUT_IDS[0]}/telemetry/latest").json())
    assert len(latest.readings) == 3 and all(r.tick_index == 1 for r in latest.readings)
    assert len(d.EnvironmentalTelemetry.model_validate(client.get(f"/api/v1/missions/{MISSION_ID}/telemetry/latest").json()).readings) == 2


def test_exact_idempotent_replay_after_later_ticks_and_stop(client, adapter):
    create_key, step_key, stop_key = (str(uuid4()) for _ in range(3))
    created = post(client, key=create_key)
    run = created.json()
    original_step = step(client, run, key=step_key)
    assert step(client, run).status_code == 200
    stopped = post(client, f"{BASE}/{run['id']}/stop", None, stop_key)
    before = deepcopy(adapter._state)
    assert post(client, key=create_key).json() == created.json()
    assert step(client, run, key=step_key).json() == original_step.json()
    assert post(client, f"{BASE}/{run['id']}/stop", None, stop_key).json() == stopped.json()
    assert adapter._state == before
    conflict = post(client, body=BODY | {"seed": 99}, key=create_key)
    assert conflict.status_code == 409 and conflict.json()["error"]["code"] == "idempotency_conflict"
    assert step(client, run, steps=2, key=step_key).status_code == 409


@pytest.mark.parametrize("patch_body", [{"scenario": "unknown"}, {"seed": 1.2}, {"step_seconds": 0}, {"interval_seconds": 61}, {"astronaut_id": "invalid"}, {"simulation_start_at": "2026-11-15T12:00:00"}])
def test_invalid_creation(client, patch_body):
    assert post(client, body=BODY | patch_body).status_code == 422


@pytest.mark.parametrize("steps", [0, 61, 1.5])
def test_invalid_steps(client, steps):
    run = post(client).json()
    assert step(client, run, steps=steps).status_code == 422


def test_missing_header_astronaut_run_and_global_single_run(client):
    assert client.post(BASE, json=BODY).status_code == 422
    assert post(client, body=BODY | {"astronaut_id": stable_id("missing")}).status_code == 404
    assert client.get(f"{BASE}/{stable_id('missing')}").status_code == 404
    assert post(client).status_code == 201
    assert post(client, body=BODY | {"astronaut_id": ASTRONAUT_IDS[1]}).status_code == 409


def test_state_controls_have_no_background_generation(client, adapter):
    run = post(client).json()
    resumed = post(client, f"{BASE}/{run['id']}/resume", None)
    assert resumed.json()["status"] == "running"
    assert step(client, run).status_code == 409
    before = deepcopy(adapter._state)
    for _ in range(3):
        for path in (BASE, f"{BASE}/{run['id']}", "/api/v1/simulation/scenarios",
                     f"/api/v1/astronauts/{ASTRONAUT_IDS[0]}/telemetry/latest", f"/api/v1/missions/{MISSION_ID}/telemetry/latest",
                     f"/api/v1/missions/{MISSION_ID}/environmental-readings"):
            assert client.get(path).status_code == 200
    assert adapter._state == before
    assert post(client, f"{BASE}/{run['id']}/pause", None).json()["status"] == "paused"
    assert step(client, run).status_code == 200
    assert post(client, f"{BASE}/{run['id']}/stop", None).json()["status"] == "stopped"
    assert step(client, run).status_code == 409
    assert post(client, f"{BASE}/{run['id']}/resume", None).status_code == 409


@pytest.mark.parametrize("repository,method", [(EnvironmentalReadingRepository, "add_many"), (SimulationRunRepository, "update"), (CommandReceiptRepository, "add"), (MemoryUnitOfWork, "commit")])
def test_tick_failure_rolls_back_readings_progress_and_receipt(client, adapter, repository, method):
    run = post(client).json()
    before = deepcopy(adapter._state)
    key = str(uuid4())
    with patch.object(repository, method, side_effect=RepositoryUnavailable("injected")):
        assert step(client, run, key=key).status_code == 503
    assert adapter._state == before
    assert step(client, run, key=key).status_code == 200


def test_concurrent_same_tick_command_is_written_once(adapter):
    service = SimulationService(adapter)
    run = service.create(d.SimulationRunCreate.model_validate(BODY), str(uuid4()))
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: service.steps(run.id, d.SimulationSteps(steps=1), key), range(2)))
    assert results[0] == results[1]
    assert len(adapter._state["health_readings"]) == 3
    assert len(adapter._state["environmental_readings"]) == 2


def test_default_seeded_run_can_be_stopped_and_replaced():
    with TestClient(create_app(Settings())) as client:
        seeded = client.get(BASE).json()["items"][0]
        assert post(client, f"{BASE}/{seeded['id']}/stop", None).status_code == 200
        assert post(client).status_code == 201
