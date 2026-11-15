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
from app.repositories.memory.adapter import AssessmentRepository, CommandReceiptRepository, HealthReadingRepository, MemoryUnitOfWork
from app.services.checkins import CheckinService
from app.services.initial_assessment import assess_checkin
from astroguard_contracts import dto as d
from astroguard_contracts.errors import ConcurrentWrite, RepositoryUnavailable
from astroguard_contracts.fixtures import ASTRONAUT_IDS, representative_fixtures, stable_id

DAY = "2026-11-15"
BODY = {"checkin_date": DAY, "observed_at": f"{DAY}T12:15:00Z", "context": "resting",
        "readings": [{"indicator": "heart_rate", "value": 72, "unit": "bpm"},
                     {"indicator": "blood_pressure_systolic", "value": 120, "unit": "mmHg"},
                     {"indicator": "blood_pressure_diastolic", "value": 80, "unit": "mmHg"}],
        "sleep_hours": 7.5, "mood": 4, "stress": 2, "exercise_minutes": 30,
        "symptoms": [], "notes": "Fictional manual check-in"}
PATH = f"/api/v1/astronauts/{ASTRONAUT_IDS[0]}/checkins"


@pytest.fixture
def adapter():
    return MemoryAdapterFactory()


@pytest.fixture
def client(adapter):
    with TestClient(create_app(Settings(), adapter), raise_server_exceptions=False) as client:
        yield client


def submit(client, body=None, key=None, path=PATH):
    return client.post(path, json=BODY if body is None else body,
                       headers={"Idempotency-Key": str(uuid4()) if key is None else key})


def counts(adapter):
    return {name: len(records) for name, records in adapter._state.items()}


def test_full_atomic_submission_and_readback(client, adapter):
    before = counts(adapter)
    response = submit(client)
    assert response.status_code == 201, response.text
    result = d.CheckinResult.model_validate(response.json())
    assert result.checkin.astronaut_id == ASTRONAUT_IDS[0]
    assert result.checkin.sleep_hours == 7.5 and len(result.readings) == 3
    assert all(r.source == "manual" and r.checkin_id == result.checkin.id for r in result.readings)
    assert result.assessment.status == "insufficient_data" and result.alerts == []
    after = counts(adapter)
    assert after["checkins"] == before["checkins"] + 1
    assert after["health_readings"] == before["health_readings"] + 3
    assert after["assessments"] == before["assessments"] + 1
    assert after["command_receipts"] == before["command_receipts"] + 1
    detail = client.get(f"{PATH}/{result.checkin.id}")
    assert detail.status_code == 200 and d.DailyCheckin.model_validate(detail.json()) == result.checkin
    page = client.get(PATH, params={"from": f"{DAY}T00:00:00Z", "to": "2026-11-16T00:00:00Z"}).json()
    assert page["total"] == 1 and page["items"][0]["id"] == result.checkin.id
    readings = client.get(PATH.replace("checkins", "readings"), params={"from": f"{DAY}T00:00:00Z", "source": "manual"}).json()
    assert {r["id"] for r in readings["items"]} == {r.id for r in result.readings}
    assessment = client.get(PATH.replace("checkins", f"assessments/{result.assessment.id}"))
    assert d.Assessment.model_validate(assessment.json()) == result.assessment


@pytest.mark.parametrize("extra", [{"sleep_hours": 0}, {"notes": "A fictional observation"}, {"symptoms": ["Fictional symptom"]}, {"exercise_minutes": 0}])
def test_optional_fields_are_not_invented(client, extra):
    response = submit(client, {"checkin_date": DAY, "observed_at": f"{DAY}T10:00:00Z", "context": "unspecified", **extra})
    assert response.status_code == 201
    result = response.json()
    assert result["readings"] == [] and result["checkin"]["readings"] == []
    assert result["checkin"]["mood"] is None
    for key, value in extra.items():
        assert result["checkin"][key] == value


@pytest.mark.parametrize("patch_body", [
    {"sleep_hours": 25}, {"mood": 0}, {"stress": 6}, {"exercise_minutes": 1.5},
    {"observed_at": "2026-11-15T12:00:00"}, {"checkin_date": "2026-11-14"}, {"context": "invalid"},
    {"readings": [{"indicator": "heart_rate", "value": 72, "unit": "ppm"}]},
    {"readings": [{"indicator": "cabin_co2", "value": 800, "unit": "ppm"}]},
    {"readings": [{"indicator": "spo2", "value": 101, "unit": "%"}]},
    {"readings": [{"indicator": "blood_pressure_systolic", "value": 120, "unit": "mmHg"}]},
    {"symptoms": ["x"] * 21}, {"notes": "x" * 2001},
])
def test_invalid_request_rolls_back(client, adapter, patch_body):
    before = counts(adapter)
    response = submit(client, BODY | patch_body)
    assert response.status_code == 422
    assert d.ErrorResponse.model_validate(response.json()).error.code == "validation_error"
    assert counts(adapter) == before


@pytest.mark.parametrize("body", [{}, {"checkin_date": DAY, "observed_at": f"{DAY}T12:00:00Z", "context": "resting"}])
def test_missing_fields_or_observations(client, body):
    assert submit(client, body).status_code == 422


@pytest.mark.parametrize("key", [None, "invalid-uuid"])
def test_required_uuid_idempotency_header(client, key):
    headers = {} if key is None else {"Idempotency-Key": key}
    assert client.post(PATH, json=BODY, headers=headers).status_code == 422


@pytest.mark.parametrize("id,status", [("invalid-id", 422), (stable_id("missing-astronaut"), 404)])
def test_missing_or_invalid_astronaut(client, id, status):
    assert submit(client, path=f"/api/v1/astronauts/{id}/checkins").status_code == status


def test_same_command_replay_returns_exact_result(client, adapter):
    key = str(uuid4())
    first = submit(client, key=key)
    before = counts(adapter)
    second = submit(client, key=key)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert counts(adapter) == before
    reordered = submit(client, BODY | {"readings": list(reversed(BODY["readings"]))}, key=key)
    assert reordered.json() == first.json()


def test_conflicting_key_and_duplicate_day(client, adapter):
    key = str(uuid4())
    assert submit(client, key=key).status_code == 201
    before = counts(adapter)
    conflict = submit(client, BODY | {"notes": "Changed"}, key=key)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"
    assert submit(client).status_code == 409
    assert submit(client, key=key, path=f"/api/v1/astronauts/{ASTRONAUT_IDS[1]}/checkins").status_code == 409
    assert counts(adapter) == before


@pytest.mark.parametrize("repository,method", [(HealthReadingRepository, "add_many"), (AssessmentRepository, "add"), (CommandReceiptRepository, "add"), (MemoryUnitOfWork, "commit")])
def test_failure_at_each_write_boundary_leaves_no_partial_records(client, adapter, repository, method):
    before = deepcopy(adapter._state)
    key = str(uuid4())
    with patch.object(repository, method, side_effect=RepositoryUnavailable("injected failure")):
        response = submit(client, key=key)
    assert response.status_code == 503
    assert adapter._state == before
    assert submit(client, key=key).status_code == 201


def test_assessment_failure_also_rolls_back(client, adapter):
    before = deepcopy(adapter._state)
    with patch("app.services.checkins.assess_checkin", side_effect=RuntimeError("injected evaluator failure")):
        response = submit(client)
    assert response.status_code == 500
    assert adapter._state == before


def test_read_ownership_and_no_get_generation(client, adapter):
    result = submit(client).json()
    other = f"/api/v1/astronauts/{ASTRONAUT_IDS[1]}"
    assert client.get(f"{other}/checkins/{result['checkin']['id']}").status_code == 404
    assert client.get(f"{other}/assessments/{result['assessment']['id']}").status_code == 404
    before = deepcopy(adapter._state)
    for _ in range(2):
        for resource in ("checkins", "readings", "assessments"):
            response = client.get(PATH.replace("checkins", resource))
            assert response.status_code == 200
    assert adapter._state == before


def test_empty_history_and_date_validation():
    fixtures = representative_fixtures()
    fixtures = {key: records for key, records in fixtures.items() if key in ("missions", "astronauts")}
    with TestClient(create_app(Settings(), MemoryAdapterFactory(fixtures))) as client:
        assert client.get(PATH).json()["items"] == []
        assert client.get(PATH, params={"from": "2026-11-16T00:00:00Z", "to": "2026-11-15T00:00:00Z"}).status_code == 422


def test_cors_allows_idempotent_json_post(client):
    response = client.options(PATH, headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "Content-Type,Idempotency-Key"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_educational_assessment_determinism_and_symptom_evidence(client):
    result = d.CheckinResult.model_validate(submit(client, BODY | {"symptoms": ["Fictional symptom"]}).json())
    expected = assess_checkin(result.checkin, result.readings)
    assert expected == result.assessment == assess_checkin(result.checkin, result.readings)
    assert expected.status == "review_suggested"
    assert expected.coverage.insufficient_rule_ids == ["demo_oxygen", "demo_temperature", "demo_cabin_co2", "demo_radiation", "clinical_context"]
    assert any(e.record_id == result.checkin.id and e.indicator == "reported_symptom_count" and e.value == 1 for r in expected.results for e in r.evidence)


def test_concurrent_identical_commands_create_one_result(adapter):
    service = CheckinService(adapter)
    key = str(uuid4())
    request = d.CheckinCreate.model_validate(BODY)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: service.create(ASTRONAUT_IDS[0], request, key), range(2)))
    assert results[0] == results[1]
    with adapter.create_uow() as uow:
        assert uow.checkins.get_for_date(ASTRONAUT_IDS[0], datetime.fromisoformat(DAY).date()).id == results[0].checkin.id


def test_retry_after_concurrent_write_uses_new_snapshot(client):
    original = MemoryUnitOfWork.commit
    calls = 0
    def commit(uow):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ConcurrentWrite("injected race")
        return original(uow)
    with patch.object(MemoryUnitOfWork, "commit", commit):
        assert submit(client).status_code == 201
    assert calls == 2


def test_post_then_separate_get_requests_reuse_one_application_store():
    # Use the real application lifespan, not an injected factory, to catch an
    # accidental per-request factory in dependency injection or service setup.
    with TestClient(create_app(Settings())) as client:
        factory = client.app.state.adapter
        result = submit(client).json()
        id = result["checkin"]["id"]
        for _ in range(3):
            assert client.get(f"{PATH}/{id}").json() == result["checkin"]
            history = client.get(PATH).json()
            assert any(record["id"] == id for record in history["items"])
            assert client.app.state.adapter is factory
        other = client.get(f"/api/v1/astronauts/{ASTRONAUT_IDS[1]}/checkins").json()
        assert all(record["id"] != id for record in other["items"])
        assert all(record["astronaut_id"] == ASTRONAUT_IDS[1] for record in other["items"])


def test_independent_units_of_work_see_the_same_committed_checkin(adapter):
    first_reader = adapter.create_uow()
    second_reader = adapter.create_uow()
    assert first_reader is not second_reader
    result = CheckinService(adapter).create(ASTRONAUT_IDS[0], d.CheckinCreate.model_validate(BODY), str(uuid4()))
    # New transaction snapshots must read the committed factory state, even if
    # their UnitOfWork objects were allocated before the service committed.
    with first_reader as first:
        assert first.checkins.get(result.checkin.id) == result.checkin
    with second_reader as second:
        assert second.checkins.get(result.checkin.id) == result.checkin
        assert second.assessments.get(result.assessment.id) == result.assessment
