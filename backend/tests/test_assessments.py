from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.core.config import Settings
from app.repositories.memory import MemoryAdapterFactory
from app.repositories.memory.adapter import AlertRepository, AssessmentRepository, CommandReceiptRepository
from app.services.initial_assessment import evaluate, RULES
from astroguard_contracts import dto as d
from astroguard_contracts.errors import RepositoryUnavailable
from astroguard_contracts.fixtures import ASTRONAUT_IDS, MISSION_ID, representative_fixtures

ASTRONAUT = ASTRONAUT_IDS[0]
BASE = f"/api/v1/astronauts/{ASTRONAUT}"
NOW = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)


@pytest.fixture
def adapter():
    return MemoryAdapterFactory({name: records for name, records in representative_fixtures().items() if name in ('missions', 'astronauts')})


@pytest.fixture
def client(adapter):
    with TestClient(create_app(Settings(), adapter), raise_server_exceptions=False) as client:
        yield client


def post(client, path, body=None, key=None):
    return client.post(path, headers={"Idempotency-Key": key or str(uuid4())}, **({"json": body} if body is not None else {}))


def checkin(day=15, value=130):
    return {"checkin_date": f"2026-11-{day}", "observed_at": f"2026-11-{day}T12:00:00Z", "context": "resting",
        "readings": [{"indicator": "heart_rate", "value": value, "unit": "bpm"}]}


@pytest.mark.parametrize('rule,indicator,direction,review,elevated,unit,kind', RULES)
def test_each_rule_boundary_explanation_units_and_missing_data(rule, indicator, direction, review, elevated, unit, kind):
    def assess(value):
        health, environment, daily = [], [], None
        if kind == 'daily_checkin':
            daily = d.DailyCheckin(id=str(uuid4()), created_at=NOW, astronaut_id=ASTRONAUT,
                checkin_date=NOW.date(), observed_at=NOW, context='resting', **{indicator: value})
        elif kind == 'health_reading':
            health = [d.HealthReading(id=str(uuid4()), created_at=NOW, astronaut_id=ASTRONAUT,
                observed_at=NOW, context='resting', source='manual', indicator=indicator, value=value, unit=unit)]
        else:
            environment = [d.EnvironmentalReading(id=str(uuid4()), created_at=NOW, mission_id=MISSION_ID,
                observed_at=NOW, simulation_run_id=str(uuid4()), tick_index=0, indicator=indicator, value=value, unit=unit)]
        first = evaluate(ASTRONAUT, health, environment, daily, NOW)
        assert first == evaluate(ASTRONAUT, health, environment, daily, NOW)
        return next(result for result in first.results if result.rule_id == rule)
    low = elevated - .1 if direction == 'low_strict' else elevated
    result = assess(int(low) if indicator in ('stress', 'mood') else low)
    assert result.outcome == 'triggered' and result.workflow_status == 'crew_medical_review'
    assert result.evidence[0].unit == unit
    assert indicator in result.explanation and 'Not a clinical threshold' in result.explanation
    if direction == 'low_strict':
        assert assess(review).outcome == 'not_triggered'
    else:
        assert assess(review).workflow_status == 'review_suggested'
    missing = next(result for result in evaluate(ASTRONAUT, [], [], None, NOW).results if result.rule_id == rule)
    assert missing.outcome == 'insufficient_data' and missing.evidence == [] and missing.missing_data == [indicator]


def test_missing_data_is_not_fabricated_and_disclaimer_present():
    result = evaluate(ASTRONAUT, [], [], None, NOW)
    assert result.status == 'insufficient_data'
    assert not any(rule.evidence for rule in result.results)
    assert all(rule.outcome == 'insufficient_data' for rule in result.results)
    assert 'Clinical evaluation is not implemented' in result.results[-1].explanation


def test_complete_nontriggering_observations_are_not_a_safety_clearance():
    run = d.SimulationRun(id=str(uuid4()), created_at=NOW, mission_id=MISSION_ID, astronaut_id=ASTRONAUT,
        scenario='routine', seed=42, simulation_start_at=NOW, scenario_version='telemetry-v1')
    from app.simulation.generator import generate_tick
    health, environment = generate_tick(run, 0, NOW)
    daily = d.DailyCheckin(id=str(uuid4()), created_at=NOW, astronaut_id=ASTRONAUT, observed_at=NOW, checkin_date=NOW.date(),
        context='resting', sleep_hours=8, stress=2, mood=4)
    result = evaluate(ASTRONAUT, health, environment, daily, NOW)
    assert result.status == 'no_rule_triggered'
    assert result.coverage.insufficient_rule_ids == ['clinical_context']


def test_alert_lifecycle_duplicate_prevention_and_exact_command_replay(client, adapter):
    key = str(uuid4())
    first = post(client, BASE + '/checkins', checkin(), key)
    assert first.status_code == 201, first.text
    alert = first.json()['alerts'][0]
    assert alert['workflow_status'] == 'crew_medical_review' and alert['state'] == 'open'
    assert alert['latest_assessment_id'] == first.json()['assessment']['id']
    ackkey = str(uuid4())
    ackpath = BASE + f"/alerts/{alert['id']}/acknowledgement"
    ack = post(client, ackpath, key=ackkey)
    assert ack.status_code == 200 and ack.json()['acknowledged_at']
    assert post(client, ackpath).json() == ack.json()
    second = post(client, BASE + '/checkins', checkin(16, 115)).json()
    assert second['alerts'] == []
    page = client.get(BASE + '/alerts').json()
    assert page['total'] == 1 and page['items'][0]['state'] == 'acknowledged'
    assert page['items'][0]['latest_assessment_id'] == second['assessment']['id']
    third = post(client, BASE + '/checkins', checkin(17, 72)).json()
    latest = client.get(BASE + '/alerts').json()['items'][0]
    assert latest['state'] == 'resolved' and latest['resolved_at']
    assert latest['latest_assessment_id'] == third['assessment']['id']
    assert post(client, ackpath).status_code == 409
    # Replaying an old command preserves its original response, despite newer lifecycle revisions.
    assert post(client, ackpath, key=ackkey).json() == ack.json()
    assert post(client, BASE + '/checkins', checkin(), key).json() == first.json()
    reopened = post(client, BASE + '/checkins', checkin(18)).json()['alerts'][0]
    assert reopened['id'] != alert['id'] and reopened['state'] == 'open'
    assert client.get(BASE + '/alerts?state=open').json()['total'] == 1


def test_unknown_data_does_not_resolve_alert(client):
    post(client, BASE + '/checkins', checkin())
    body = {"checkin_date": '2026-11-16', 'observed_at': '2026-11-16T12:00:00Z', 'context': 'resting', 'notes': 'Fictional note only'}
    post(client, BASE + '/checkins', body)
    assert client.get(BASE + '/alerts').json()['items'][0]['state'] == 'open'


def test_backdated_checkin_cannot_resolve_a_newer_observation_alert(client):
    original = post(client, BASE + '/checkins', checkin(17)).json()
    assert post(client, BASE + '/checkins', checkin(15, 72)).status_code == 201
    alert = client.get(BASE + '/alerts').json()['items'][0]
    assert alert['state'] == 'open' and alert['latest_assessment_id'] == original['assessment']['id']


def test_long_symptom_reports_fit_contract_and_explain_count_without_diagnosis(client):
    body = {"checkin_date": '2026-11-15', 'observed_at': '2026-11-15T12:00:00Z', 'context': 'resting', 'symptoms': ['Fictional ' + 'x' * 90] * 20}
    response = post(client, BASE + '/checkins', body)
    assert response.status_code == 201, response.text
    result = d.CheckinResult.model_validate(response.json())
    assert result.assessment.status == 'crew_medical_review'
    rule = next(r for r in result.assessment.results if r.rule_id == 'reported_symptoms')
    assert rule.evidence[0].value == 20 and 'No diagnosis' in rule.explanation


def test_acknowledgement_write_failure_rolls_back_alert_and_receipt(client, adapter):
    alert = post(client, BASE + '/checkins', checkin()).json()['alerts'][0]
    before = deepcopy(adapter._state)
    with patch.object(CommandReceiptRepository, 'add', side_effect=RepositoryUnavailable('Injected failure')):
        assert post(client, BASE + f"/alerts/{alert['id']}/acknowledgement").status_code == 503
    assert adapter._state == before


def test_evaluation_deduplicates_inputs_and_gets_do_not_write(client, adapter):
    post(client, BASE + '/checkins', checkin())
    key = str(uuid4())
    first = post(client, BASE + '/assessments', key=key)
    assert first.status_code == 200, first.text
    before = deepcopy(adapter._state)
    assert post(client, BASE + '/assessments', key=key).json() == first.json()
    assert adapter._state == before
    assert post(client, BASE + '/assessments').json()['id'] == first.json()['id']
    assert len(adapter._state['assessments']) == 1
    before = deepcopy(adapter._state)
    for path in ('alerts', 'assessments', f"assessments/{first.json()['id']}"):
        assert client.get(BASE + '/' + path).status_code == 200
    assert before == adapter._state
    assert post(client, BASE + '/checkins', checkin(16), key).status_code == 409


def test_astronaut_isolation_and_required_keys(client):
    alert = post(client, BASE + '/checkins', checkin()).json()['alerts'][0]
    other = f'/api/v1/astronauts/{ASTRONAUT_IDS[1]}'
    assert client.get(other + '/alerts').json()['items'] == []
    assert post(client, other + f"/alerts/{alert['id']}/acknowledgement").status_code == 404
    assert client.get(other + f"/assessments/{alert['latest_assessment_id']}").status_code == 404
    assert client.post(BASE + '/assessments').status_code == 422
    assert client.get(BASE + '/alerts?state=invalid').status_code == 422


@pytest.mark.parametrize('repository', [AlertRepository, AssessmentRepository, CommandReceiptRepository])
def test_checkin_atomic_failure_rolls_back_everything(client, adapter, repository):
    before = deepcopy(adapter._state)
    with patch.object(repository, 'add', side_effect=RepositoryUnavailable('Injected failure')):
        assert post(client, BASE + '/checkins', checkin()).status_code == 503
    assert adapter._state == before


@pytest.mark.parametrize('repository', [AlertRepository, AssessmentRepository, CommandReceiptRepository])
def test_simulation_assessment_and_alert_failure_rolls_back_entire_tick_batch(client, adapter, repository):
    run = post(client, '/api/v1/simulation/runs', {"astronaut_id": ASTRONAUT, 'scenario': 'environmental_change', 'seed': 42, 'simulation_start_at': NOW.isoformat()}).json()
    before = deepcopy(adapter._state)
    with patch.object(repository, 'add', side_effect=RepositoryUnavailable('Injected failure')):
        response = post(client, f"/api/v1/simulation/runs/{run['id']}/steps", {'steps': 20})
        assert response.status_code == 503, response.text
    assert adapter._state == before


def test_ticks_generate_explainable_assessments_and_unique_environmental_alerts(client, adapter):
    run = post(client, '/api/v1/simulation/runs', {"astronaut_id": ASTRONAUT, 'scenario': 'environmental_change', 'seed': 42, 'simulation_start_at': NOW.isoformat()}).json()
    key = str(uuid4()); path = f"/api/v1/simulation/runs/{run['id']}/steps"
    result = post(client, path, {'steps': 20}, key)
    assert result.status_code == 200, result.text
    assessments = client.get(BASE + '/assessments').json()['items']
    assert len(assessments) == 20
    assert any(rule['evidence'] and rule['evidence'][0]['record_type'] == 'environmental_reading' for rule in assessments[0]['results'])
    assert next(rule for rule in assessments[0]['results'] if rule['rule_id'] == 'demo_sleep')['outcome'] == 'insufficient_data'
    alerts = client.get(BASE + '/alerts').json()['items']
    assert len(alerts) == 2 and {alert['rule_id'] for alert in alerts} == {'demo_cabin_co2', 'demo_radiation'}
    assert all(alert['latest_assessment_id'] == assessments[0]['id'] for alert in alerts)
    before = deepcopy(adapter._state)
    assert post(client, path, {'steps': 20}, key).json() == result.json()
    assert before == adapter._state
