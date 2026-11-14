"""Canonical wire values. These are application labels, not clinical standards."""
from enum import StrEnum


class MissionEnvironment(StrEnum):
    MICROGRAVITY = "microgravity"
    LUNAR = "lunar"
    MARTIAN = "martian"
    EARTH_ANALOG = "earth_analog"


class HealthIndicator(StrEnum):
    HEART_RATE = "heart_rate"
    SYSTOLIC = "blood_pressure_systolic"
    DIASTOLIC = "blood_pressure_diastolic"
    GLUCOSE = "blood_glucose"
    TEMPERATURE = "body_temperature"
    SPO2 = "spo2"


class EnvironmentalIndicator(StrEnum):
    CABIN_CO2 = "cabin_co2"
    RADIATION_DOSE_RATE = "radiation_dose_rate"


class Unit(StrEnum):
    BPM = "bpm"
    MMHG = "mmHg"
    MG_DL = "mg/dL"
    DEGC = "degC"
    PERCENT = "%"
    PPM = "ppm"
    USV_H = "uSv/h"


HEALTH_UNITS = {
    HealthIndicator.HEART_RATE: Unit.BPM,
    HealthIndicator.SYSTOLIC: Unit.MMHG,
    HealthIndicator.DIASTOLIC: Unit.MMHG,
    HealthIndicator.GLUCOSE: Unit.MG_DL,
    HealthIndicator.TEMPERATURE: Unit.DEGC,
    HealthIndicator.SPO2: Unit.PERCENT,
}
ENVIRONMENTAL_UNITS = {
    EnvironmentalIndicator.CABIN_CO2: Unit.PPM,
    EnvironmentalIndicator.RADIATION_DOSE_RATE: Unit.USV_H,
}


class Source(StrEnum):
    MANUAL = "manual"
    SIMULATED = "simulated"


class ObservationContext(StrEnum):
    RESTING = "resting"
    EXERCISE = "exercise"
    RECOVERY = "recovery"
    UNSPECIFIED = "unspecified"


class AssessmentStatus(StrEnum):
    INSUFFICIENT_DATA = "insufficient_data"
    NO_RULE_TRIGGERED = "no_rule_triggered"
    REVIEW_SUGGESTED = "review_suggested"
    CREW_MEDICAL_REVIEW = "crew_medical_review"


class RuleOutcome(StrEnum):
    TRIGGERED = "triggered"
    NOT_TRIGGERED = "not_triggered"
    INSUFFICIENT_DATA = "insufficient_data"
    NOT_APPLICABLE = "not_applicable"


class AlertState(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class Scenario(StrEnum):
    ROUTINE = "routine"
    EXERCISE_RECOVERY = "exercise_recovery"
    REDUCED_SLEEP_STRESS = "reduced_sleep_stress"
    UNUSUAL_HEALTH_TREND = "unusual_health_trend"
    ENVIRONMENTAL_CHANGE = "environmental_change"


class RunStatus(StrEnum):
    PAUSED = "paused"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
