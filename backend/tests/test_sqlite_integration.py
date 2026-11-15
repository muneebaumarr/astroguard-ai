from uuid import uuid4
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from astroguard_contracts.fixtures import ASTRONAUT_IDS
from astroguard_db import SqliteAdapterFactory
from astroguard_db.migrate import upgrade
from astroguard_db.seed import seed
from app.core.config import Settings
from app.main import create_app
from astroguard_db.repositories import SqliteCommandReceiptRepository
from app.services.checkins import CheckinService
from astroguard_contracts import dto as d
from astroguard_contracts.errors import RepositoryUnavailable, Conflict
from astroguard_db.repositories import SqliteAlertRepository, SqliteAssessmentRepository
from astroguard_db.uow import SqliteUnitOfWork
from app.import_memory_export import import_export

BASE = f'/api/v1/astronauts/{ASTRONAUT_IDS[0]}'
BODY = {'checkin_date': '2030-01-01', 'observed_at': '2030-01-01T12:00:00Z', 'context': 'resting',
    'readings': [{'indicator': 'heart_rate', 'value': 130, 'unit': 'bpm'}, {'indicator': 'spo2', 'value': 94, 'unit': '%'},
                 {'indicator': 'body_temperature', 'value': 38, 'unit': 'degC'}], 'sleep_hours': 3, 'stress': 5}


@pytest.fixture
def settings(tmp_path):
    url = 'sqlite:///' + (tmp_path / 'integration.db').as_posix()
    upgrade(url)
    factory = SqliteAdapterFactory(url)
    try:
        assert seed(factory)
    finally:
        factory.dispose()
    return Settings(repository_backend='sqlite', database_url=url)


def post(client, path, body=None, key=None):
    return client.post(path, headers={'Idempotency-Key': key or str(uuid4())}, **({'json': body} if body is not None else {}))


def test_multivital_checkin_replay_remains_identical_after_sqlite_reconstruction(settings):
    with TestClient(create_app(settings)) as client:
        key = str(uuid4())
        response = post(client, BASE + '/checkins', BODY, key)
        assert response.status_code == 201, response.text
        assert post(client, BASE + '/checkins', BODY, key).json() == response.json()


def test_concurrent_same_command_replays_instead_of_duplicate_conflict(settings):
    factory = SqliteAdapterFactory(settings.database_url)
    barrier, lock, arrivals = Barrier(2), Lock(), [0]
    original = SqliteCommandReceiptRepository.get
    key = str(uuid4())
    def synchronized(repository, command_id):
        result = original(repository, command_id)
        with lock:
            arrivals[0] += 1
            first = arrivals[0] <= 2
        if first:
            barrier.wait(timeout=10)
        return result
    try:
        service = CheckinService(factory)
        with patch.object(SqliteCommandReceiptRepository, 'get', synchronized), ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(service.create, ASTRONAUT_IDS[0], d.CheckinCreate.model_validate(BODY), key) for _ in range(2)]
            assert futures[0].result() == futures[1].result()
    finally:
        factory.dispose()


def stop_seeded_run(client):
    for run in client.get('/api/v1/simulation/runs').json()['items']:
        if run['status'] in ('running', 'paused'):
            assert post(client, f"/api/v1/simulation/runs/{run['id']}/stop").status_code == 200


def test_full_workflow_survives_new_application_lifespan_and_command_replay(settings):
    checkin_key, tick_key, ack_key = (str(uuid4()) for _ in range(3))
    with TestClient(create_app(settings)) as client:
        assert client.get('/api/v1/health').json()['adapter'] == 'sqlite'
        assert client.get('/api/v1/ready').json()['ready']
        saved = post(client, BASE + '/checkins', BODY, checkin_key)
        assert saved.status_code == 201, saved.text
        saved = saved.json()
        assert saved['alerts'] and saved['assessment']['status'] == 'crew_medical_review'
        alert_id = saved['alerts'][0]['id']
        ack_path = BASE + f'/alerts/{alert_id}/acknowledgement'
        acknowledged = post(client, ack_path, key=ack_key).json()
        assert acknowledged['state'] == 'acknowledged'
        stop_seeded_run(client)
        created = post(client, '/api/v1/simulation/runs', {'astronaut_id': ASTRONAUT_IDS[0], 'scenario': 'environmental_change',
            'seed': 42, 'simulation_start_at': '2030-01-02T12:00:00Z'}).json()
        run_id = created['id']
        stepped = post(client, f'/api/v1/simulation/runs/{run_id}/steps', {'steps': 12}, tick_key)
        assert stepped.status_code == 200, stepped.text
        stepped = stepped.json()
        health = client.get(BASE + '/readings', params={'simulation_run_id': run_id}).json()
        assert health['total'] == 36
        mission_id = created['mission_id']
        environment = client.get(f'/api/v1/missions/{mission_id}/environmental-readings', params={'simulation_run_id': run_id}).json()
        assert environment['total'] == 24
        assert all(item['source'] == 'simulated' for item in health['items'])
        alerts = client.get(BASE + '/alerts').json()
        assert any(item['rule_id'] == 'demo_cabin_co2' for item in alerts['items'])
        # Missing self-reports in simulation must not clear check-in flags.
        assert any(item['rule_id'] == 'demo_sleep' and item['state'] != 'resolved' for item in alerts['items'])
        assessments = client.get(BASE + '/assessments').json()
    # Owned factory was disposed; this is a fresh app/connection pool reopening the same file.
    with TestClient(create_app(settings)) as restarted:
        detail = restarted.get(BASE + '/checkins/' + saved['checkin']['id']).json()
        assert detail == saved['checkin']
        assert restarted.get(BASE + '/readings', params={'simulation_run_id': run_id}).json() == health
        assert restarted.get(f'/api/v1/missions/{mission_id}/environmental-readings', params={'simulation_run_id': run_id}).json() == environment
        assert restarted.get(BASE + '/assessments').json() == assessments
        assert restarted.get(BASE + '/alerts').json() == alerts
        assert post(restarted, BASE + '/checkins', BODY, checkin_key).json() == saved
        assert post(restarted, f'/api/v1/simulation/runs/{run_id}/steps', {'steps': 12}, tick_key).json() == stepped
        assert post(restarted, ack_path, key=ack_key).json() == acknowledged
        assert restarted.get(BASE + '/assessments').json() == assessments
        other = f'/api/v1/astronauts/{ASTRONAUT_IDS[1]}'
        assert restarted.get(other + '/checkins/' + saved['checkin']['id']).status_code == 404
        assert post(restarted, other + f'/alerts/{alert_id}/acknowledgement').status_code == 404
        assert post(restarted, BASE + '/checkins', BODY | {'notes': 'different'}, checkin_key).status_code == 409


def counts(factory):
    with factory.create_uow() as uow:
        return {
            'checkins': uow.checkins.list(ASTRONAUT_IDS[0], d.CheckinQuery()).total,
            'readings': uow.health_readings.list(ASTRONAUT_IDS[0], d.HealthReadingQuery()).total,
            'assessments': uow.assessments.list(ASTRONAUT_IDS[0], d.AssessmentQuery()).total,
            'alerts': uow.alerts.list(ASTRONAUT_IDS[0], d.AlertQuery()).total,
        }


@pytest.mark.parametrize('repository,method', [(SqliteAlertRepository, 'add'), (SqliteAssessmentRepository, 'add'),
    (SqliteCommandReceiptRepository, 'add'), (SqliteUnitOfWork, 'commit')])
def test_sqlite_checkin_failure_rolls_back_records_and_receipt(settings, repository, method):
    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        adapter = client.app.state.adapter
        before = counts(adapter); key = str(uuid4())
        with patch.object(repository, method, side_effect=RepositoryUnavailable('Injected failure')):
            assert post(client, BASE + '/checkins', BODY, key).status_code == 503
        assert counts(adapter) == before
        with adapter.create_uow() as uow:
            assert uow.command_receipts.get(key) is None
        assert post(client, BASE + '/checkins', BODY, key).status_code == 201


def test_sqlite_tick_batch_failure_rolls_back_generated_readings_alerts_and_progress(settings):
    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        stop_seeded_run(client)
        run = post(client, '/api/v1/simulation/runs', {'astronaut_id': ASTRONAUT_IDS[0], 'scenario': 'environmental_change',
            'seed': 42, 'simulation_start_at': '2030-01-01T12:00:00Z'}).json()
        adapter = client.app.state.adapter; before = counts(adapter); key = str(uuid4())
        with patch.object(SqliteAlertRepository, 'add', side_effect=RepositoryUnavailable('Injected failure')):
            response = post(client, f"/api/v1/simulation/runs/{run['id']}/steps", {'steps': 12}, key)
            assert response.status_code == 503
        assert counts(adapter) == before
        assert client.get(f"/api/v1/simulation/runs/{run['id']}").json()['last_tick_index'] == -1
        assert client.get(f"/api/v1/missions/{run['mission_id']}/environmental-readings", params={'simulation_run_id': run['id']}).json()['total'] == 0
        with adapter.create_uow() as uow:
            assert uow.command_receipts.get(key) is None


def test_unmigrated_database_fails_readiness_without_seed_or_memory_fallback(tmp_path):
    settings = Settings(repository_backend='sqlite', database_url='sqlite:///' + (tmp_path / 'unmigrated.db').as_posix())
    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        response = client.get('/api/v1/ready')
        assert response.status_code == 503 and response.json()['adapter'] == 'sqlite'
        assert client.get('/api/v1/astronauts').status_code == 503
        # The catalog remains independent and read-only even when storage isn't ready.
        assert client.get('/api/v1/hazards').status_code == 200


@pytest.mark.parametrize('url', ['sqlite:///:memory:', 'postgresql://localhost/example'])
def test_sqlite_configuration_does_not_silently_use_other_storage(url):
    with pytest.raises(RuntimeError, match='no memory fallback'):
        with TestClient(create_app(Settings(repository_backend='sqlite', database_url=url))):
            pass


def test_both_adapters_include_acknowledged_unresolved_alerts_in_open_filter(settings):
    from app.repositories.memory import MemoryAdapterFactory
    for adapter in (MemoryAdapterFactory(), SqliteAdapterFactory(settings.database_url)):
        try:
            with adapter.create_uow() as uow:
                alert = uow.alerts.list(ASTRONAUT_IDS[0], d.AlertQuery()).items[0]
                acknowledged = d.Alert.model_validate(alert.model_dump() | {'state': 'acknowledged', 'acknowledged_at': alert.opened_at})
                uow.alerts.update(acknowledged); uow.commit()
            with adapter.create_uow() as uow:
                assert uow.alerts.list(ASTRONAUT_IDS[0], d.AlertQuery(state='open')).items == [acknowledged]
                assert uow.alerts.get_open(ASTRONAUT_IDS[0], alert.rule_id) == acknowledged
        finally:
            if hasattr(adapter, 'dispose'): adapter.dispose()
            else: adapter.close()


def test_injected_adapter_is_not_disposed_by_app(settings):
    adapter = SqliteAdapterFactory(settings.database_url)
    try:
        with patch.object(adapter, 'dispose', wraps=adapter.dispose) as dispose:
            with TestClient(create_app(settings, adapter)) as client:
                assert client.get('/api/v1/ready').status_code == 200
            dispose.assert_not_called()
        assert adapter.check_ready().ready
    finally:
        adapter.dispose()


def test_committed_checkin_and_idempotency_survive_a_separate_python_process(settings):
    key = str(uuid4())
    with TestClient(create_app(settings)) as client:
        saved = post(client, BASE + '/checkins', BODY, key).json()
    script = '''
import json, sys
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.config import Settings
with TestClient(create_app(Settings(repository_backend="sqlite", database_url=sys.argv[1]))) as client:
    result = client.post(sys.argv[2] + "/checkins", json=json.loads(sys.argv[3]), headers={"Idempotency-Key": sys.argv[4]})
    assert result.status_code == 201, result.text
    print(json.dumps(result.json()))
'''
    result = subprocess.run([sys.executable, '-c', script, settings.database_url, BASE, json.dumps(BODY), key],
        capture_output=True, text=True, check=True, timeout=30)
    assert json.loads(result.stdout) == saved


def memory_export():
    from app.repositories.memory import MemoryAdapterFactory
    memory = MemoryAdapterFactory()
    CheckinService(memory).create(ASTRONAUT_IDS[0], d.CheckinCreate.model_validate(BODY), str(uuid4()))
    names = {'missions': 'missions', 'astronauts': 'astronauts', 'simulation_runs': 'simulation_runs',
        'checkins': 'checkins', 'readings': 'health_readings', 'environmental_readings': 'environmental_readings',
        'assessments': 'assessments', 'alerts': 'alerts'}
    return {'format': 'astroguard-pre-sqlite-api-export-v1', **{name: [record.model_dump(mode='json') for record in memory._state[table].values()] for name, table in names.items()}}


def test_memory_export_imports_observations_atomically_and_replays_without_duplicates(settings):
    adapter = SqliteAdapterFactory(settings.database_url)
    payload = memory_export()
    try:
        added = import_export(adapter, payload)
        assert added['checkins'] == 1 and added['readings'] == 3 and added['assessments'] == 1
        assert added['alerts'] > 0
        assert not any(import_export(adapter, payload).values())
        with adapter.create_uow() as uow:
            record = next(item for item in payload['checkins'] if item['checkin_date'] == BODY['checkin_date'])
            assert uow.checkins.get(record['id']) == d.DailyCheckin.model_validate(record)
    finally:
        adapter.dispose()


def test_failed_memory_import_leaves_no_partial_observations(settings):
    adapter = SqliteAdapterFactory(settings.database_url)
    payload = memory_export()
    # Missing linked health values must not silently produce an incomplete imported check-in.
    payload['readings'] = [item for item in payload['readings'] if item.get('observed_at') != BODY['observed_at']]
    try:
        before = counts(adapter)
        with pytest.raises(Conflict):
            import_export(adapter, payload)
        assert counts(adapter) == before
    finally:
        adapter.dispose()
