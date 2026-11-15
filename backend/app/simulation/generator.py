from datetime import timedelta
from hashlib import sha256
from uuid import UUID, uuid5

from astroguard_contracts import dto as d
from astroguard_contracts.enums import Scenario

VERSION = "telemetry-v1"
DESCRIPTIONS = {
    Scenario.ROUTINE: "Small fictional variations around fixed demonstration values.",
    Scenario.EXERCISE_RECOVERY: "A repeating twelve-tick exercise and recovery illustration.",
    Scenario.REDUCED_SLEEP_STRESS: "A fictional physiological illustration only; sleep and stress are not inferred or recorded.",
    Scenario.UNUSUAL_HEALTH_TREND: "A bounded fictional trend, without diagnosis or severity classification.",
    Scenario.ENVIRONMENTAL_CHANGE: "Independent fictional cabin CO2 and radiation-rate changes.",
}


def scenarios():
    return [d.ScenarioDefinition(scenario=scenario, version=VERSION, description=description,
        required_fixture_context=[], expected_outcomes=["Three fictional health and two cabin readings per tick; no clinical interpretation."])
        for scenario, description in DESCRIPTIONS.items()]


def generate_tick(run: d.SimulationRun, tick: int, created_at):
    """Values depend on version, scenario, seed, tick and indicator, never wall time."""
    if run.scenario_version not in (VERSION, "demo-v1"):
        raise ValueError("Unsupported simulation version")
    def noise(indicator, amplitude):
        digest = sha256(f"{run.scenario_version}|{run.scenario}|{run.seed}|{tick}|{indicator}".encode()).digest()
        return (int.from_bytes(digest[:8], "big") / (2**64 - 1) * 2 - 1) * amplitude

    values = {"heart_rate": 72.0, "spo2": 98.0, "body_temperature": 36.7,
              "cabin_co2": 800.0, "radiation_dose_rate": 10.0}
    context = "resting"
    phase = tick % 12
    if run.scenario == Scenario.EXERCISE_RECOVERY:
        context = "exercise" if phase < 6 else "recovery"
        intensity = phase if phase < 6 else 11 - phase
        values["heart_rate"] += intensity * 7
        values["body_temperature"] += intensity * 0.04
    elif run.scenario == Scenario.REDUCED_SLEEP_STRESS:
        values["heart_rate"] += 8
    elif run.scenario == Scenario.UNUSUAL_HEALTH_TREND:
        values["heart_rate"] += min(tick, 20) * 1.5
        values["spo2"] -= min(tick, 20) * 0.15
    elif run.scenario == Scenario.ENVIRONMENTAL_CHANGE:
        values["cabin_co2"] += min(tick, 20) * 80
        values["radiation_dose_rate"] += min(tick, 20) * 1.5
    amplitudes = {"heart_rate": 2, "spo2": 0.4, "body_temperature": 0.1, "cabin_co2": 20, "radiation_dose_rate": 0.2}
    values = {name: round(value + noise(name, amplitudes[name]), 2) for name, value in values.items()}
    observed_at = run.simulation_start_at + timedelta(seconds=tick * run.step_seconds)
    common = dict(created_at=created_at, observed_at=observed_at, source="simulated", simulation_run_id=run.id, tick_index=tick)
    health = [d.HealthReading(id=str(uuid5(UUID(run.id), f"health:{tick}:{indicator}")),
        astronaut_id=run.astronaut_id, context=context, indicator=indicator, value=values[indicator], unit=unit, **common)
        for indicator, unit in (("heart_rate", "bpm"), ("spo2", "%"), ("body_temperature", "degC"))]
    environment = [d.EnvironmentalReading(id=str(uuid5(UUID(run.id), f"environment:{tick}:{indicator}")),
        mission_id=run.mission_id, indicator=indicator, value=values[indicator], unit=unit, **common)
        for indicator, unit in (("cabin_co2", "ppm"), ("radiation_dose_rate", "uSv/h"))]
    return health, environment
