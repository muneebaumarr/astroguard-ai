import inspect
from datetime import timedelta

import pytest

from app.repositories.memory import MemoryAdapterFactory
from astroguard_contracts import dto as d, repositories as protocols
from astroguard_contracts.errors import ConcurrentWrite, Conflict, RepositoryUnavailable
from astroguard_contracts.fixtures import ASTRONAUT_IDS, EPOCH, MISSION_ID, representative_fixtures, stable_id


def new_mission(name="new"):
    return d.Mission(id=stable_id(f"mission:{name}"), created_at=EPOCH, name=name,
        environment="earth_analog", started_at=EPOCH)


def test_commit_explicit_rollback_and_uncommitted_exit():
    factory = MemoryAdapterFactory()
    with factory.create_uow() as uow:
        uow.missions.add(new_mission("committed"))
        uow.commit()
        uow.missions.add(new_mission("rolled-back"))
        uow.rollback()
        assert uow.missions.get(new_mission("rolled-back").id) is None
        uow.missions.add(new_mission("uncommitted"))
    with factory.create_uow() as uow:
        assert uow.missions.get(new_mission("committed").id)
        assert uow.missions.get(new_mission("uncommitted").id) is None


def test_exception_rolls_back_all_repositories():
    factory = MemoryAdapterFactory()
    with pytest.raises(ValueError, match="abort"):
        with factory.create_uow() as uow:
            mission = uow.missions.add(new_mission())
            uow.astronauts.add(d.Astronaut(id=stable_id("crew:new"), created_at=EPOCH,
                mission_id=mission.id, display_name="Fictional New Crew", role="Demo"))
            raise ValueError("abort")
    with factory.create_uow() as uow:
        assert uow.missions.get(new_mission().id) is None
        assert uow.astronauts.get(stable_id("crew:new")) is None


def test_invalid_cross_record_commit_leaves_store_unchanged():
    factory = MemoryAdapterFactory()
    with pytest.raises(Conflict):
        with factory.create_uow() as uow:
            uow.missions.add(new_mission())
            uow.astronauts.add(d.Astronaut(id=stable_id("orphan"), created_at=EPOCH,
                mission_id=stable_id("missing"), display_name="Orphan Demo", role="Demo"))
            uow.commit()
    with factory.create_uow() as uow:
        assert uow.missions.get(new_mission().id) is None


def test_concurrent_writes_do_not_lose_records():
    factory = MemoryAdapterFactory()
    with factory.create_uow() as first, factory.create_uow() as second:
        first.missions.add(new_mission("first"))
        second.missions.add(new_mission("second"))
        first.commit()
        with pytest.raises(ConcurrentWrite):
            second.commit()
    with factory.create_uow() as uow:
        assert uow.missions.get(new_mission("first").id)
        assert uow.missions.get(new_mission("second").id) is None


def test_returned_records_and_fixtures_are_detached():
    factory = MemoryAdapterFactory()
    with factory.create_uow() as uow:
        checkin = uow.checkins.list(ASTRONAUT_IDS[0], d.CheckinQuery()).items[0]
        checkin.readings.clear()
        assert uow.checkins.get(checkin.id).readings
        uow.commit()
    assert representative_fixtures()["checkins"][0].readings


def test_fixture_loading_and_read_protocols():
    factory = MemoryAdapterFactory()
    fixtures = representative_fixtures()
    with factory.create_uow() as uow:
        assert uow.missions.get(MISSION_ID) == fixtures["missions"][0]
        assert uow.astronauts.list(d.AstronautQuery(mission_id=MISSION_ID)).total == 2
        checkin = fixtures["checkins"][0]
        assert uow.checkins.get_for_date(checkin.astronaut_id, checkin.checkin_date) == checkin
        assert uow.health_readings.latest_by_indicator(ASTRONAUT_IDS[0], "manual")["heart_rate"].value == 76
        assert set(uow.environmental_readings.latest_by_indicator(MISSION_ID)) == {"cabin_co2", "radiation_dose_rate"}
        assessment = fixtures["assessments"][0]
        assert uow.assessments.get_by_fingerprint(assessment.astronaut_id, assessment.ruleset_version, assessment.input_fingerprint) == assessment
        alert = fixtures["alerts"][0]
        assert uow.alerts.get_open(alert.astronaut_id, alert.rule_id) == alert
        assert uow.simulation_runs.get_active() == fixtures["simulation_runs"][0]
        assert uow.command_receipts.get(fixtures["command_receipts"][0].id) == fixtures["command_receipts"][0]


def test_filtering_exclusive_end_and_pagination():
    with MemoryAdapterFactory().create_uow() as uow:
        query = d.HealthReadingQuery.model_validate({"from": EPOCH, "to": EPOCH + timedelta(days=2), "source": "manual", "limit": 1, "offset": 1})
        page = uow.health_readings.list(ASTRONAUT_IDS[0], query)
        assert page.total == 2 and len(page.items) == 1
        assert page.items[0].observed_at == EPOCH + timedelta(days=1)
        assert uow.environmental_readings.list(MISSION_ID, d.EnvironmentalReadingQuery(indicator="cabin_co2")).total == 1


def test_batch_duplicate_does_not_partially_write():
    with MemoryAdapterFactory().create_uow() as uow:
        original = representative_fixtures()["health_readings"][0]
        fresh = d.HealthReading.model_validate(original.model_dump() | {"id": stable_id("fresh-reading"), "checkin_id": None})
        with pytest.raises(Conflict):
            uow.health_readings.add_many([fresh, original])
        assert uow.health_readings.list(original.astronaut_id, d.HealthReadingQuery()).total == 8


def test_unique_constraints_and_progress_conflicts():
    factory = MemoryAdapterFactory()
    with factory.create_uow() as uow:
        run = uow.simulation_runs.get_active()
        with pytest.raises(ConcurrentWrite):
            uow.simulation_runs.update(run, expected_last_tick=999)
        updated = d.SimulationRun.model_validate(run.model_dump() | {"last_tick_index": 1})
        assert uow.simulation_runs.update(updated, expected_last_tick=0).last_tick_index == 1
        uow.commit()
    with pytest.raises(Conflict):
        with factory.create_uow() as uow:
            uow.simulation_runs.add(d.SimulationRun.model_validate(run.model_dump() | {"id": stable_id("another-active-run")}))
            uow.commit()


def test_alert_update_and_receipt_add():
    factory = MemoryAdapterFactory()
    with factory.create_uow() as uow:
        alert = representative_fixtures()["alerts"][0]
        updated = d.Alert.model_validate(alert.model_dump() | {"state": "acknowledged", "acknowledged_at": EPOCH})
        uow.alerts.update(updated)
        assert uow.alerts.get_open(alert.astronaut_id, alert.rule_id).state == "acknowledged"
        receipt = d.CommandReceipt(id=stable_id("command:new"), created_at=EPOCH,
            operation="test", request_hash="f" * 64, result_type="alert", result_id=alert.id)
        uow.command_receipts.add(receipt)
        uow.commit()
    with factory.create_uow() as uow:
        assert uow.command_receipts.get(receipt.id) == receipt


def test_unit_of_work_is_not_usable_outside_transaction():
    uow = MemoryAdapterFactory().create_uow()
    with pytest.raises(RepositoryUnavailable):
        uow.commit()
    with uow:
        assert uow.missions.get(MISSION_ID)
    with pytest.raises(RepositoryUnavailable):
        uow.missions.get(MISSION_ID)


def test_shared_method_names_and_argument_signatures():
    mapping = {"missions": protocols.MissionRepository, "astronauts": protocols.AstronautRepository,
        "checkins": protocols.CheckinRepository, "health_readings": protocols.HealthReadingRepository,
        "environmental_readings": protocols.EnvironmentalReadingRepository,
        "assessments": protocols.AssessmentRepository, "alerts": protocols.AlertRepository,
        "simulation_runs": protocols.SimulationRunRepository, "command_receipts": protocols.CommandReceiptRepository}
    with MemoryAdapterFactory().create_uow() as uow:
        for name, protocol in mapping.items():
            implementation = type(getattr(uow, name))
            for method, member in vars(protocol).items():
                if inspect.isfunction(member) and not method.startswith('_'):
                    expected = inspect.signature(member)
                    actual = inspect.signature(getattr(implementation, method))
                    assert actual.parameters == expected.parameters, (name, method)
                    assert actual.return_annotation == expected.return_annotation, (name, method)
