from datetime import timedelta

import pytest

from astroguard_contracts.dto import (
    Alert, AlertQuery, AssessmentQuery, Astronaut, AstronautQuery, CheckinQuery,
    EnvironmentalReadingQuery, HealthReading, HealthReadingQuery, Mission, MissionQuery,
    SimulationRun, SimulationRunQuery,
)
from astroguard_contracts.enums import (
    AlertState, EnvironmentalIndicator, HealthIndicator, RunStatus, Source,
)
from astroguard_contracts.errors import ConcurrentWrite, Conflict
from astroguard_contracts.fixtures import (
    ASTRONAUT_IDS, EPOCH, MISSION_ID, RUN_ID, representative_fixtures, stable_id,
)
from astroguard_db.seed import seed

A0, A1 = ASTRONAUT_IDS


# ---------------------------------------------------------------------------
# Seed + round trip: every fixture comes back exactly as it went in
# ---------------------------------------------------------------------------
def test_seed_is_idempotent(seeded):
    assert seed(seeded) is False
    with seeded.create_uow() as uow:
        assert uow.missions.list(MissionQuery()).total == 1
        assert uow.astronauts.list(AstronautQuery()).total == 2


def test_fixture_round_trip(seeded):
    fx = representative_fixtures()
    with seeded.create_uow() as uow:
        for m in fx["missions"]:
            assert uow.missions.get(m.id) == m
        for a in fx["astronauts"]:
            assert uow.astronauts.get(a.id) == a
        for c in fx["checkins"]:
            assert uow.checkins.get(c.id) == c
        for x in fx["assessments"]:
            assert uow.assessments.get(x.id) == x
            assert uow.assessments.get_by_fingerprint(x.astronaut_id, x.ruleset_version, x.input_fingerprint) == x
        for x in fx["alerts"]:
            assert uow.alerts.get(x.id) == x
        for x in fx["simulation_runs"]:
            assert uow.simulation_runs.get(x.id) == x
        for x in fx["command_receipts"]:
            assert uow.command_receipts.get(x.id) == x
        for astronaut_id in ASTRONAUT_IDS:
            expected = sorted((r for r in fx["health_readings"] if r.astronaut_id == astronaut_id),
                              key=lambda r: (r.observed_at, r.id))
            page = uow.health_readings.list(astronaut_id, HealthReadingQuery(limit=1000))
            assert page.items == expected
            assert page.total == len(expected)
        expected_env = sorted(fx["environmental_readings"], key=lambda r: (r.observed_at, r.id))
        assert uow.environmental_readings.list(MISSION_ID, EnvironmentalReadingQuery()).items == expected_env


def test_get_missing_returns_none(seeded):
    missing = stable_id("does-not-exist")
    with seeded.create_uow() as uow:
        assert uow.missions.get(missing) is None
        assert uow.astronauts.get(missing) is None
        assert uow.checkins.get(missing) is None
        assert uow.assessments.get(missing) is None
        assert uow.alerts.get(missing) is None
        assert uow.simulation_runs.get(missing) is None
        assert uow.command_receipts.get(missing) is None


def test_checkin_get_for_date_rebuilds_readings(seeded):
    fx = representative_fixtures()
    first = fx["checkins"][0]
    with seeded.create_uow() as uow:
        found = uow.checkins.get_for_date(first.astronaut_id, first.checkin_date)
        assert found == first
        assert [r.indicator for r in found.readings] == [HealthIndicator.HEART_RATE]
        assert uow.checkins.get_for_date(first.astronaut_id, first.checkin_date + timedelta(days=100)) is None


# ---------------------------------------------------------------------------
# Constraints -> Conflict
# ---------------------------------------------------------------------------
def test_foreign_keys_are_enforced(factory):
    ghost = Astronaut(id=stable_id("astronaut:ghost"), created_at=EPOCH,
                      mission_id=stable_id("mission:missing"), display_name="Ghost", role="Demo crew")
    with factory.create_uow() as uow:
        with pytest.raises(Conflict):
            uow.astronauts.add(ghost)


def test_one_checkin_per_astronaut_per_day(seeded):
    duplicate = representative_fixtures()["checkins"][0].model_copy(update={"id": stable_id("checkin:dup")})
    with seeded.create_uow() as uow:
        with pytest.raises(Conflict):
            uow.checkins.add(duplicate)


def test_assessment_fingerprint_is_unique(seeded):
    duplicate = representative_fixtures()["assessments"][0].model_copy(update={"id": stable_id("assessment:dup")})
    with seeded.create_uow() as uow:
        with pytest.raises(Conflict):
            uow.assessments.add(duplicate)


def test_command_receipt_is_unique(seeded):
    receipt = representative_fixtures()["command_receipts"][0]
    with seeded.create_uow() as uow:
        with pytest.raises(Conflict):
            uow.command_receipts.add(receipt)


def test_simulated_tick_indicator_is_unique(seeded):
    simulated = next(r for r in representative_fixtures()["health_readings"] if r.source == Source.SIMULATED)
    duplicate = simulated.model_copy(update={"id": stable_id("reading:dup")})
    with seeded.create_uow() as uow:
        with pytest.raises(Conflict):
            uow.health_readings.add_many([duplicate])


def test_reading_must_match_checkin_owner(seeded):
    checkin = representative_fixtures()["checkins"][0]  # belongs to A0
    wrong = HealthReading(id=stable_id("reading:wrong-owner"), created_at=EPOCH, astronaut_id=A1,
                          observed_at=EPOCH, source="manual", context="resting",
                          checkin_id=checkin.id, indicator="spo2", value=97, unit="%")
    with seeded.create_uow() as uow:
        with pytest.raises(Conflict):
            uow.health_readings.add_many([wrong])


# ---------------------------------------------------------------------------
# Ordering, filters, pagination, latest values
# ---------------------------------------------------------------------------
def test_history_filters_and_pagination(seeded):
    with seeded.create_uow() as uow:
        window = HealthReadingQuery(**{"from": EPOCH + timedelta(days=1), "to": EPOCH + timedelta(days=3)},
                                    indicator="heart_rate")
        page = uow.health_readings.list(A0, window)
        assert [r.value for r in page.items] == [71.0, 72.0]  # from included, to excluded

        page = uow.health_readings.list(A0, HealthReadingQuery(limit=2, offset=2, indicator="heart_rate"))
        assert page.total == 7
        assert [r.value for r in page.items] == [72.0, 73.0]

        simulated = uow.health_readings.list(A0, HealthReadingQuery(source="simulated"))
        assert [r.indicator for r in simulated.items] == [HealthIndicator.SPO2]

        checkins = uow.checkins.list(A0, CheckinQuery(**{"from": EPOCH, "to": EPOCH + timedelta(days=2)}))
        assert [c.observed_at for c in checkins.items] == [EPOCH, EPOCH + timedelta(days=1)]
        assert checkins.total == 2


def test_assessments_and_alerts_descend(seeded):
    fx = representative_fixtures()
    with seeded.create_uow() as uow:
        page = uow.assessments.list(A0, AssessmentQuery())
        assert [a.id for a in page.items] == sorted((a.id for a in fx["assessments"]), reverse=True)
        alerts = uow.alerts.list(A0, AlertQuery())
        assert [a.id for a in alerts.items] == [fx["alerts"][0].id]


def test_latest_by_indicator_breaks_ties_by_id(seeded):
    later = EPOCH + timedelta(days=30)
    ids = [stable_id("tie:1"), stable_id("tie:2")]
    readings = [HealthReading(id=i, created_at=later, astronaut_id=A1, observed_at=later, source="manual",
                              context="resting", indicator="heart_rate", value=80, unit="bpm") for i in ids]
    with seeded.create_uow() as uow:
        uow.health_readings.add_many(readings)
        uow.commit()
    with seeded.create_uow() as uow:
        latest = uow.health_readings.latest_by_indicator(A1)
        assert latest[HealthIndicator.HEART_RATE].id == max(ids)
        simulated_only = uow.health_readings.latest_by_indicator(A0, source=Source.SIMULATED)
        assert set(simulated_only) == {HealthIndicator.SPO2}
        environment = uow.environmental_readings.latest_by_indicator(MISSION_ID)
        assert set(environment) == {EnvironmentalIndicator.CABIN_CO2, EnvironmentalIndicator.RADIATION_DOSE_RATE}


# ---------------------------------------------------------------------------
# Alerts lifecycle
# ---------------------------------------------------------------------------
def test_alert_lifecycle(seeded):
    fx = representative_fixtures()
    alert = fx["alerts"][0]
    triggered_id = alert.first_assessment_id
    acknowledged = alert.model_copy(update={"state": AlertState.ACKNOWLEDGED,
                                            "acknowledged_at": EPOCH + timedelta(hours=1)})
    with seeded.create_uow() as uow:
        uow.alerts.update(acknowledged)
        uow.commit()

    second = Alert(id=stable_id("alert:second"), created_at=EPOCH, astronaut_id=A0, rule_id="demo_pattern",
                   workflow_status="review_suggested", state="open", first_assessment_id=triggered_id,
                   latest_assessment_id=triggered_id, opened_at=EPOCH + timedelta(hours=3))
    with seeded.create_uow() as uow:
        assert uow.alerts.get_open(A0, "demo_pattern") == acknowledged  # acknowledged still counts as open
        assert uow.alerts.list(A0, AlertQuery(state="open")).total == 1
        with pytest.raises(Conflict):
            uow.alerts.add(second)  # only one active alert per astronaut and rule

    resolved = acknowledged.model_copy(update={"state": AlertState.RESOLVED,
                                               "resolved_at": EPOCH + timedelta(hours=2)})
    with seeded.create_uow() as uow:
        uow.alerts.update(resolved)
        uow.alerts.add(second)
        uow.commit()
    with seeded.create_uow() as uow:
        assert uow.alerts.get_open(A0, "demo_pattern") == second
        assert uow.alerts.list(A0, AlertQuery(state="resolved")).items == [resolved]


# ---------------------------------------------------------------------------
# Simulation runs
# ---------------------------------------------------------------------------
def _new_run(name, mission_id=MISSION_ID):
    return SimulationRun(id=stable_id(name), created_at=EPOCH, astronaut_id=A0, mission_id=mission_id,
                         scenario="routine", seed=1, scenario_version="demo-v1", simulation_start_at=EPOCH)


def test_simulation_run_rules(seeded):
    with seeded.create_uow() as uow:
        with pytest.raises(Conflict):
            uow.simulation_runs.add(_new_run("run:wrong-mission", stable_id("mission:other")))
    with seeded.create_uow() as uow:
        with pytest.raises(Conflict):
            uow.simulation_runs.add(_new_run("run:second-active"))  # fixture run is already active

    with seeded.create_uow() as uow:
        run = uow.simulation_runs.get(RUN_ID)
        running = run.model_copy(update={"status": RunStatus.RUNNING, "started_at": EPOCH, "last_tick_index": 1})
        uow.simulation_runs.update(running, expected_last_tick=0)
        uow.commit()

    with seeded.create_uow() as uow:
        stale = running.model_copy(update={"last_tick_index": 2})
        with pytest.raises(ConcurrentWrite):
            uow.simulation_runs.update(stale, expected_last_tick=0)

    with seeded.create_uow() as uow:
        assert uow.simulation_runs.get(RUN_ID).last_tick_index == 1
        assert uow.simulation_runs.get_active().id == RUN_ID
        stopped = running.model_copy(update={"status": RunStatus.STOPPED})
        uow.simulation_runs.update(stopped, expected_last_tick=1)
        uow.simulation_runs.add(_new_run("run:next"))
        uow.commit()

    with seeded.create_uow() as uow:
        assert uow.simulation_runs.get_active().id == stable_id("run:next")
        assert uow.simulation_runs.list(SimulationRunQuery(status="stopped")).items[0].id == RUN_ID
        restart = uow.simulation_runs.get(RUN_ID).model_copy(update={"status": RunStatus.RUNNING})
        with pytest.raises(Conflict):
            uow.simulation_runs.update(restart, expected_last_tick=1)  # stopped is terminal


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------
def _mission(name):
    return Mission(id=stable_id(name), created_at=EPOCH, name=name, environment="lunar", started_at=EPOCH)


def test_exception_rolls_back(factory):
    mission = _mission("mission:exception")
    with pytest.raises(RuntimeError):
        with factory.create_uow() as uow:
            uow.missions.add(mission)
            raise RuntimeError("boom")
    with factory.create_uow() as uow:
        assert uow.missions.get(mission.id) is None


def test_missing_commit_rolls_back(factory):
    mission = _mission("mission:no-commit")
    with factory.create_uow() as uow:
        uow.missions.add(mission)
    with factory.create_uow() as uow:
        assert uow.missions.get(mission.id) is None


def test_explicit_rollback_and_commit(factory):
    rolled_back = _mission("mission:rollback")
    kept = _mission("mission:kept")
    with factory.create_uow() as uow:
        uow.missions.add(rolled_back)
        uow.rollback()
        uow.missions.add(kept)
        uow.commit()
    with factory.create_uow() as uow:
        assert uow.missions.get(rolled_back.id) is None
        assert uow.missions.get(kept.id) == kept
