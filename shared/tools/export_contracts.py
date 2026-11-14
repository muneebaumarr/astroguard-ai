"""Explicit documentation export, never executed during package import/install."""
import ast
import json
from pathlib import Path

from astroguard_contracts import dto as d
from astroguard_contracts.fixtures import EPOCH, representative_fixtures, stable_id

ROOT = Path(__file__).resolve().parents[1]


def sample_models():
    f = representative_fixtures()
    mission, astronaut = f["missions"][0], f["astronauts"][0]
    checkin, assessment = f["checkins"][0], f["assessments"][0]
    readings = [r for r in f["health_readings"] if r.checkin_id == checkin.id]
    source = d.SourceReference(title="NASA hazards", url="https://www.nasa.gov/hrp/hazards/")
    article = d.GuidanceArticle(slug="heart-rate", title="Understanding heart rate",
        indicators=["heart_rate"], hazard_slugs=["gravity_fields"],
        educational_text="Fictional monitoring context, not a diagnosis.",
        limitations="No clinical thresholds or treatment instructions.", references=[source],
        reviewed_on=EPOCH.date())
    samples = {
        "Mission": mission, "Astronaut": astronaut, "DailyCheckin": checkin,
        "HealthReading": readings[0], "EnvironmentalReading": f["environmental_readings"][0],
        "Assessment": assessment, "Alert": f["alerts"][0],
        "SimulationRun": f["simulation_runs"][0], "CommandReceipt": f["command_receipts"][0],
        "MissionCreate": d.MissionCreate.model_validate(mission.model_dump(exclude={"id", "created_at", "is_demo"})),
        "AstronautCreate": d.AstronautCreate.model_validate(astronaut.model_dump(exclude={"id", "created_at", "is_demo"})),
        "CheckinCreate": d.CheckinCreate.model_validate(checkin.model_dump(exclude={"id", "created_at", "is_demo", "astronaut_id"})),
        "ManualReadingBatch": d.ManualReadingBatch(observed_at=EPOCH, context="resting", readings=checkin.readings),
        "SimulationRunCreate": d.SimulationRunCreate(astronaut_id=astronaut.id, scenario="routine", seed=42, simulation_start_at=EPOCH),
        "CheckinResult": d.CheckinResult(checkin=checkin, readings=readings, assessment=assessment, alerts=[]),
        "ReadingBatchResult": d.ReadingBatchResult(readings=readings, assessment=assessment, alerts=[]),
        "Dashboard": d.Dashboard(astronaut=astronaut, mission=mission, latest_health=readings,
            latest_environment=f["environmental_readings"], checkin=checkin, assessment=assessment,
            alerts=[], simulation_run=f["simulation_runs"][0], as_of=EPOCH),
        "HealthResponse": d.HealthResponse(contract_version="0.1.0", adapter="memory"),
        "ReadinessResult": d.ReadinessResult(ready=True, adapter="sqlite"),
        "ErrorResponse": d.ErrorResponse(error=d.ErrorDetail(code="not_found", message="Astronaut not found",
            request_id=stable_id("request:not-found"))),
        "HealthTelemetry": d.HealthTelemetry(astronaut_id=astronaut.id,
            readings=[f["health_readings"][-1]], as_of=EPOCH),
        "EnvironmentalTelemetry": d.EnvironmentalTelemetry(mission_id=mission.id,
            readings=f["environmental_readings"], as_of=EPOCH),
        "SimulationSteps": d.SimulationSteps(steps=1),
        "SimulationStepResult": d.SimulationStepResult(run=f["simulation_runs"][0],
            generated_health_count=1, generated_environmental_count=2),
        "ScenarioDefinition": d.ScenarioDefinition(scenario="routine", version="demo-v1",
            description="Fictional routine scenario", required_fixture_context=[],
            expected_outcomes=["No demonstration pattern after sufficient evidence"]),
        "GuidanceArticle": article,
        "Hazard": d.Hazard(slug="space_radiation", title="Space radiation",
            description="Educational hazard overview", related_indicators=["radiation_dose_rate"],
            monitoring_limitations="Cabin rate does not measure personal exposure", references=[source]),
    }
    for name in ("Mission", "Astronaut", "DailyCheckin", "HealthReading", "EnvironmentalReading",
                 "Assessment", "Alert", "SimulationRun", "ScenarioDefinition", "GuidanceArticle", "Hazard"):
        model = type(samples[name])
        items = [samples[name]]
        samples[f"Page[{name}]"] = d.Page[model](items=items, total=1, limit=100, offset=0)
    return samples


def export():
    fixtures = representative_fixtures()
    (ROOT / "fixtures").mkdir(exist_ok=True)
    (ROOT / "fixtures" / "fictional.json").write_text(json.dumps(
        {k: [v.model_dump(mode="json") for v in values] for k, values in fixtures.items()},
        indent=2) + "\n", encoding="utf-8")
    samples = sample_models()
    (ROOT / "sample-responses.json").write_text(json.dumps(
        {k: v.model_dump(mode="json") for k, v in samples.items()}, indent=2) + "\n", encoding="utf-8")
    models = {name: model for name, model in vars(d).items()
              if isinstance(model, type) and issubclass(model, d.DTO) and model.__module__ == d.__name__}
    models.update({name: type(value) for name, value in samples.items()})
    (ROOT / "schema.json").write_text(json.dumps(
        {name: model.model_json_schema(by_alias=True) for name, model in models.items()},
        indent=2) + "\n", encoding="utf-8")
    source = (ROOT / "src/astroguard_contracts/repositories.py").read_text(encoding="utf-8")
    lines = source.splitlines()
    sections = ["# Exact repository interface signatures", "",
                "Generated from the protocol source. UUIDString is a canonical UUID str.",
                "All interfaces are synchronous; ellipses denote contracts, not implementations.", ""]
    for node in ast.parse(source).body:
        if isinstance(node, ast.ClassDef):
            sections += [f"## {node.name}", "", "```python"]
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AnnAssign)):
                    sections.append(lines[member.lineno - 1].strip())
            sections += ["```", ""]
    (ROOT.parent / "docs/repository-interfaces.md").write_text("\n".join(sections), encoding="utf-8")


if __name__ == "__main__":
    export()
