"""Fixed fictional definitions only: no database seeding or telemetry generation."""
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid5

from .dto import (
    Alert, Assessment, Astronaut, CommandReceipt, Coverage, DailyCheckin,
    EnvironmentalReading, HealthReading, HealthValue, Mission, RuleResult,
    SimulationRun,
)

NAMESPACE = UUID("ae5802cc-2b11-4f75-8a0d-778995b7a301")
EPOCH = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)


def stable_id(name: str) -> str:
    return str(uuid5(NAMESPACE, name))


MISSION_ID = stable_id("mission:aurora")
ASTRONAUT_IDS = (stable_id("astronaut:maya"), stable_id("astronaut:leo"))
RUN_ID = stable_id("simulation:representative")


def representative_fixtures() -> dict[str, list]:
    """Return fresh validated DTOs; callers cannot mutate subsequent fixture calls."""
    mission = Mission(id=MISSION_ID, created_at=EPOCH, name="Aurora Demo",
                      environment="microgravity", started_at=EPOCH,
                      description="Entirely fictional educational mission")
    astronauts = [Astronaut(id=identifier, created_at=EPOCH, mission_id=MISSION_ID,
                           display_name=name, role="Demo crew")
                  for identifier, name in zip(ASTRONAUT_IDS, ("Maya Demo", "Leo Demo"))]
    checkins, readings = [], []
    for astronaut in astronauts:
        for day in range(7):
            observed = EPOCH + timedelta(days=day)
            checkin_id = stable_id(f"checkin:{astronaut.id}:{day}")
            value = HealthValue(indicator="heart_rate", value=70 + day, unit="bpm")
            checkins.append(DailyCheckin(id=checkin_id, created_at=observed,
                astronaut_id=astronaut.id, checkin_date=observed.date(), observed_at=observed,
                context="resting", readings=[value], sleep_hours=7, mood=4, stress=2,
                notes="Fictional demo observation"))
            readings.append(HealthReading(id=stable_id(f"reading:{checkin_id}:heart_rate"),
                created_at=observed, astronaut_id=astronaut.id, observed_at=observed,
                source="manual", context="resting", checkin_id=checkin_id,
                **value.model_dump()))
    run = SimulationRun(id=RUN_ID, created_at=EPOCH, astronaut_id=ASTRONAUT_IDS[0],
        mission_id=MISSION_ID, scenario="routine", seed=42, scenario_version="demo-v1",
        simulation_start_at=EPOCH, last_tick_index=0)
    readings.append(HealthReading(id=stable_id("reading:simulated:0"), created_at=EPOCH,
        astronaut_id=ASTRONAUT_IDS[0], observed_at=EPOCH, source="simulated", context="resting",
        simulation_run_id=RUN_ID, tick_index=0, indicator="spo2", value=98, unit="%"))
    environment = [EnvironmentalReading(id=stable_id(f"environment:{indicator}:0"),
        created_at=EPOCH, mission_id=MISSION_ID, indicator=indicator, value=value,
        unit=unit, observed_at=EPOCH, simulation_run_id=RUN_ID, tick_index=0)
        for indicator, value, unit in (("cabin_co2", 800, "ppm"), ("radiation_dose_rate", 10, "uSv/h"))]
    assessment = Assessment(id=stable_id("assessment:representative"), created_at=EPOCH,
        astronaut_id=ASTRONAUT_IDS[0], evaluated_at=EPOCH, status="insufficient_data",
        ruleset_version="demo-v1", input_fingerprint="0" * 64,
        coverage=Coverage(insufficient_rule_ids=["resting_hr_change"]),
        results=[RuleResult(rule_id="resting_hr_change", outcome="insufficient_data",
            workflow_status="insufficient_data", explanation="Not enough fictional samples",
            missing_data=["Three baseline and three recent resting samples"])])
    triggered = Assessment.model_validate(assessment.model_dump() | {"id": stable_id("assessment:triggered"),
        "status": "review_suggested", "input_fingerprint": "1" * 64,
        "coverage": Coverage(evaluated_rule_ids=["demo_pattern"]),
        "results": [RuleResult(rule_id="demo_pattern", outcome="triggered",
            workflow_status="review_suggested", explanation="Authored fictional response example")]})
    alert = Alert(id=stable_id("alert:representative"), created_at=EPOCH,
        astronaut_id=ASTRONAUT_IDS[0], rule_id="demo_pattern", workflow_status="review_suggested",
        state="open", first_assessment_id=triggered.id, latest_assessment_id=triggered.id,
        opened_at=EPOCH)
    receipt = CommandReceipt(id=stable_id("command:representative"), created_at=EPOCH,
        operation="create_checkin", request_hash="2" * 64, result_type="daily_checkin",
        result_id=checkins[0].id)
    return {"missions": [mission], "astronauts": astronauts, "checkins": checkins,
            "health_readings": readings, "environmental_readings": environment,
            "assessments": [assessment, triggered], "alerts": [alert],
            "simulation_runs": [run], "command_receipts": [receipt]}
