import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from astroguard_contracts import API_PREFIX, dto as d, repositories as r
from astroguard_contracts.fixtures import EPOCH, representative_fixtures

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_MODELS = {
    "missions": d.Mission, "astronauts": d.Astronaut, "checkins": d.DailyCheckin,
    "health_readings": d.HealthReading, "environmental_readings": d.EnvironmentalReading,
    "assessments": d.Assessment, "alerts": d.Alert, "simulation_runs": d.SimulationRun,
    "command_receipts": d.CommandReceipt,
}


def response_model(name):
    if name.startswith("Page["):
        return d.Page[getattr(d, name[5:-1])]
    return getattr(d, name)


SAMPLES = json.loads((ROOT / "sample-responses.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", SAMPLES)
def test_sample_round_trip(name):
    model = response_model(name)
    value = model.model_validate(SAMPLES[name])
    assert model.model_validate_json(value.model_dump_json()) == value


def test_fixture_export_and_relationships():
    fixtures = representative_fixtures()
    exported = json.loads((ROOT / "fixtures/fictional.json").read_text(encoding="utf-8"))
    assert exported == {k: [v.model_dump(mode="json") for v in values] for k, values in fixtures.items()}
    assert len(fixtures["checkins"]) == 14
    ids = [v.id for records in fixtures.values() for v in records]
    assert len(ids) == len(set(ids))
    missions = {v.id: v for v in fixtures["missions"]}
    astronauts = {v.id: v for v in fixtures["astronauts"]}
    checkins = {v.id: v for v in fixtures["checkins"]}
    runs = {v.id: v for v in fixtures["simulation_runs"]}
    assessments = {v.id: v for v in fixtures["assessments"]}
    for key, records in fixtures.items():
        for record in records:
            assert FIXTURE_MODELS[key].model_validate_json(record.model_dump_json()) == record
            if hasattr(record, "astronaut_id"):
                assert record.astronaut_id in astronauts
    for astronaut in astronauts.values():
        assert astronaut.mission_id in missions
    for reading in fixtures["health_readings"]:
        if reading.checkin_id:
            checkin = checkins[reading.checkin_id]
            assert checkin.astronaut_id == reading.astronaut_id
            assert d.HealthValue(**reading.model_dump(include={"indicator", "value", "unit"})) in checkin.readings
        if reading.simulation_run_id:
            assert runs[reading.simulation_run_id].astronaut_id == reading.astronaut_id
    for reading in fixtures["environmental_readings"]:
        assert runs[reading.simulation_run_id].mission_id == reading.mission_id
    for alert in fixtures["alerts"]:
        assert assessments[alert.latest_assessment_id].astronaut_id == alert.astronaut_id
        assert assessments[alert.first_assessment_id].astronaut_id == alert.astronaut_id
    for receipt in fixtures["command_receipts"]:
        assert receipt.result_id in checkins
    fixtures["checkins"][0].readings.clear()
    assert representative_fixtures()["checkins"][0].readings


@pytest.mark.parametrize("patch", [
    {"id": "not-a-uuid"}, {"id": "AE5802CC-2B11-4F75-8A0D-778995B7A301"},
    {"observed_at": "2026-11-07T12:00:00"}, {"unit": "ppm"},
    {"indicator": "cabin_co2"}, {"value": float("nan")}, {"value": float("inf")},
    {"value": -1}, {"is_demo": False}, {"unknown": 1},
    {"simulation_run_id": representative_fixtures()["simulation_runs"][0].id},
    {"source": "simulated"},
])
def test_invalid_health(patch):
    payload = SAMPLES["HealthReading"] | patch
    with pytest.raises(ValidationError):
        d.HealthReading.model_validate(payload)


@pytest.mark.parametrize("patch", [
    {"sleep_hours": 25}, {"mood": 0}, {"stress": 6}, {"mood": True},
    {"exercise_minutes": 1441}, {"checkin_date": "2026-11-06"},
    {"notes": "x" * 2001}, {"symptoms": ["x"] * 21},
    {"readings": [{"indicator": "blood_pressure_systolic", "value": 120, "unit": "mmHg"}]},
])
def test_invalid_checkins(patch):
    with pytest.raises(ValidationError):
        d.CheckinCreate.model_validate(SAMPLES["CheckinCreate"] | patch)


def test_missing_zero_and_bounds():
    base = {"checkin_date": EPOCH.date(), "observed_at": EPOCH, "context": "resting"}
    with pytest.raises(ValidationError):
        d.CheckinCreate(**base)
    value = d.CheckinCreate(**base, sleep_hours=0)
    assert value.sleep_hours == 0 and value.mood is None
    d.HealthValue(indicator="spo2", value=100, unit="%")
    with pytest.raises(ValidationError):
        d.HealthValue(indicator="spo2", value=100.1, unit="%")
    assert d.Mission.model_validate(SAMPLES["Mission"] | {"started_at": "2026-11-07T17:00:00+05:00"}).started_at == EPOCH


@pytest.mark.parametrize("values", [
    [{"indicator": "heart_rate", "value": 70, "unit": "bpm"}] * 2,
    [{"indicator": "blood_pressure_systolic", "value": 80, "unit": "mmHg"},
     {"indicator": "blood_pressure_diastolic", "value": 90, "unit": "mmHg"}],
])
def test_invalid_batches(values):
    with pytest.raises(ValidationError):
        d.ManualReadingBatch(observed_at=EPOCH, context="resting", readings=values)


@pytest.mark.parametrize("patch", [{"indicator": "heart_rate"}, {"unit": "bpm"}, {"value": -1}, {"source": "manual"}])
def test_environment_separation(patch):
    with pytest.raises(ValidationError):
        d.EnvironmentalReading.model_validate(SAMPLES["EnvironmentalReading"] | patch)


@pytest.mark.parametrize("model,payload", [
    (d.PageQuery, {"limit": 1001}), (d.PageQuery, {"offset": -1}),
    (d.TimeQuery, {"from": "2026-11-08T00:00:00Z", "to": "2026-11-07T00:00:00Z"}),
    (d.SimulationSteps, {"steps": 0}), (d.SimulationSteps, {"steps": 61}),
    (d.SimulationRunCreate, SAMPLES["SimulationRunCreate"] | {"interval_seconds": 0}),
    (d.SimulationRunCreate, SAMPLES["SimulationRunCreate"] | {"step_seconds": 3601}),
    (d.Alert, SAMPLES["Alert"] | {"state": "resolved"}),
    (d.CommandReceipt, SAMPLES["CommandReceipt"] | {"request_hash": "invalid"}),
])
def test_structural_failures(model, payload):
    with pytest.raises(ValidationError):
        model.model_validate(payload)


def test_independent_installed_import(tmp_path):
    script = """
import sys
from astroguard_contracts import API_PREFIX, dto, repositories, fixtures
assert API_PREFIX == '/api/v1'
assert len(fixtures.representative_fixtures()['astronauts']) == 2
assert not any(n.split('.')[0] in {'backend','database','sqlalchemy','fastapi','astroguard_db'} for n in sys.modules)
print('independent import OK')
"""
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    result = subprocess.run([sys.executable, "-I", "-c", script], cwd=tmp_path,
                            env=environment, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert "independent import OK" in result.stdout


def test_protocols_remain_interfaces():
    source = (ROOT / "src/astroguard_contracts/repositories.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert API_PREFIX == "/api/v1"
    assert r.UnitOfWork._is_protocol
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for member in node.body:
                if isinstance(member, ast.FunctionDef):
                    assert member.returns is not None
                    assert len(member.body) == 1 and isinstance(member.body[0], ast.Expr)
                    assert member.body[0].value.value is Ellipsis


def test_exported_schemas_are_current():
    schemas = json.loads((ROOT / "schema.json").read_text(encoding="utf-8"))
    for name, schema in schemas.items():
        assert response_model(name).model_json_schema(by_alias=True) == schema
