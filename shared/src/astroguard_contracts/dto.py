"""Detached values for API and repository boundaries; no framework or ORM imports."""
from datetime import date, datetime, timezone
from typing import Annotated, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from .enums import (
    HEALTH_UNITS, ENVIRONMENTAL_UNITS, AlertState, AssessmentStatus,
    EnvironmentalIndicator, HealthIndicator, MissionEnvironment, ObservationContext,
    RuleOutcome, RunStatus, Scenario, Source, Unit,
)


def canonical_uuid(value: str) -> str:
    if str(UUID(value)) != value:
        raise ValueError("UUID must use canonical lowercase hyphenated string format")
    return value


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value.astimezone(timezone.utc)


UUIDString = Annotated[str, AfterValidator(canonical_uuid)]
UTCDateTime = Annotated[datetime, AfterValidator(utc)]
NonEmpty = Annotated[str, Field(min_length=1, max_length=200)]
T = TypeVar("T")


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True, frozen=True)


class Record(DTO):
    id: UUIDString
    created_at: UTCDateTime


class MissionCreate(DTO):
    name: NonEmpty
    environment: MissionEnvironment
    started_at: UTCDateTime
    ended_at: UTCDateTime | None = None
    description: str = ""

    @model_validator(mode="after")
    def chronological(self):
        if self.ended_at is not None and self.ended_at <= self.started_at:
            raise ValueError("ended_at must follow started_at")
        return self


class Mission(MissionCreate, Record):
    is_demo: Literal[True] = True


class AstronautCreate(DTO):
    mission_id: UUIDString
    display_name: NonEmpty
    role: NonEmpty


class Astronaut(AstronautCreate, Record):
    is_demo: Literal[True] = True


class HealthValue(DTO):
    indicator: HealthIndicator
    value: FiniteFloat
    unit: Unit

    @model_validator(mode="after")
    def measurement(self):
        if self.unit != HEALTH_UNITS[self.indicator]:
            raise ValueError("indicator/unit mismatch")
        if self.indicator != HealthIndicator.TEMPERATURE and self.value < 0:
            raise ValueError("measurement must be nonnegative")
        if self.indicator == HealthIndicator.SPO2 and self.value > 100:
            raise ValueError("spo2 must be at most 100 percent")
        return self


def validate_values(readings):
    values = {r.indicator: r.value for r in readings}
    if len(values) != len(readings):
        raise ValueError("duplicate indicators")
    systolic = values.get(HealthIndicator.SYSTOLIC)
    diastolic = values.get(HealthIndicator.DIASTOLIC)
    if (systolic is None) != (diastolic is None):
        raise ValueError("blood pressure requires both components")
    if systolic is not None and systolic <= diastolic:
        raise ValueError("systolic must exceed diastolic")


class HealthReading(HealthValue, Record):
    astronaut_id: UUIDString
    observed_at: UTCDateTime
    source: Source
    context: ObservationContext
    checkin_id: UUIDString | None = None
    simulation_run_id: UUIDString | None = None
    tick_index: Annotated[int, Field(ge=0, strict=True)] | None = None
    is_demo: Literal[True] = True

    @model_validator(mode="after")
    def lineage(self):
        if self.source == Source.SIMULATED:
            if self.simulation_run_id is None or self.tick_index is None or self.checkin_id is not None:
                raise ValueError("simulated reading requires run/tick and cannot link to check-in")
        elif self.simulation_run_id is not None or self.tick_index is not None:
            raise ValueError("manual reading cannot carry simulator metadata")
        return self


class EnvironmentalReading(Record):
    mission_id: UUIDString
    indicator: EnvironmentalIndicator
    value: Annotated[FiniteFloat, Field(ge=0)]
    unit: Unit
    observed_at: UTCDateTime
    source: Literal[Source.SIMULATED] = Source.SIMULATED
    simulation_run_id: UUIDString
    tick_index: Annotated[int, Field(ge=0, strict=True)]
    is_demo: Literal[True] = True

    @model_validator(mode="after")
    def measurement(self):
        if self.unit != ENVIRONMENTAL_UNITS[self.indicator]:
            raise ValueError("indicator/unit mismatch")
        return self


class CheckinCreate(DTO):
    checkin_date: date
    observed_at: UTCDateTime
    context: ObservationContext
    readings: list[HealthValue] = Field(default_factory=list)
    sleep_hours: Annotated[FiniteFloat, Field(ge=0, le=24)] | None = None
    mood: Annotated[int, Field(ge=1, le=5, strict=True)] | None = None
    stress: Annotated[int, Field(ge=1, le=5, strict=True)] | None = None
    symptoms: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(default_factory=list, max_length=20)
    exercise_minutes: Annotated[int, Field(ge=0, le=1440, strict=True)] | None = None
    notes: Annotated[str, Field(max_length=2000)] | None = None

    @model_validator(mode="after")
    def observations(self):
        if self.checkin_date != self.observed_at.date():
            raise ValueError("check-in date must match UTC observation date")
        validate_values(self.readings)
        if not self.readings and not self.symptoms and not (self.notes or "").strip() and all(
            v is None for v in (self.sleep_hours, self.mood, self.stress, self.exercise_minutes)
        ):
            raise ValueError("at least one observation is required")
        return self


class DailyCheckin(CheckinCreate, Record):
    astronaut_id: UUIDString
    is_demo: Literal[True] = True


class ManualReadingBatch(DTO):
    observed_at: UTCDateTime
    context: ObservationContext
    readings: list[HealthValue] = Field(min_length=1)

    @model_validator(mode="after")
    def observations(self):
        validate_values(self.readings)
        return self


class Evidence(DTO):
    record_id: UUIDString
    record_type: Literal["health_reading", "environmental_reading", "daily_checkin"]
    observed_at: UTCDateTime
    indicator: NonEmpty
    value: FiniteFloat
    unit: NonEmpty


class Coverage(DTO):
    evaluated_rule_ids: list[str] = Field(default_factory=list)
    insufficient_rule_ids: list[str] = Field(default_factory=list)
    not_applicable_rule_ids: list[str] = Field(default_factory=list)


class RuleResult(DTO):
    rule_id: NonEmpty
    outcome: RuleOutcome
    workflow_status: AssessmentStatus
    explanation: NonEmpty
    evidence: list[Evidence] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)
    guidance_slugs: list[str] = Field(default_factory=list)


class Assessment(Record):
    astronaut_id: UUIDString
    evaluated_at: UTCDateTime
    status: AssessmentStatus
    ruleset_version: NonEmpty
    input_fingerprint: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    coverage: Coverage
    results: list[RuleResult]


class Alert(Record):
    astronaut_id: UUIDString
    rule_id: NonEmpty
    workflow_status: Literal[AssessmentStatus.REVIEW_SUGGESTED, AssessmentStatus.CREW_MEDICAL_REVIEW]
    state: AlertState
    first_assessment_id: UUIDString
    latest_assessment_id: UUIDString
    opened_at: UTCDateTime
    acknowledged_at: UTCDateTime | None = None
    resolved_at: UTCDateTime | None = None

    @model_validator(mode="after")
    def lifecycle(self):
        if self.state == AlertState.ACKNOWLEDGED and self.acknowledged_at is None:
            raise ValueError("acknowledged alert requires timestamp")
        if (self.state == AlertState.RESOLVED) != (self.resolved_at is not None):
            raise ValueError("resolved timestamp must match state")
        if self.state == AlertState.OPEN and self.acknowledged_at is not None:
            raise ValueError("open alert cannot be acknowledged")
        if any(t is not None and t < self.opened_at for t in (self.acknowledged_at, self.resolved_at)):
            raise ValueError("alert lifecycle timestamps precede opening")
        return self


class SimulationRunCreate(DTO):
    astronaut_id: UUIDString
    scenario: Scenario
    seed: Annotated[int, Field(strict=True)]
    simulation_start_at: UTCDateTime
    interval_seconds: Annotated[int, Field(ge=1, le=60, strict=True)] = 5
    step_seconds: Annotated[int, Field(ge=1, le=3600, strict=True)] = 60


class SimulationRun(SimulationRunCreate, Record):
    mission_id: UUIDString
    scenario_version: NonEmpty
    status: RunStatus = RunStatus.PAUSED
    started_at: UTCDateTime | None = None
    last_tick_index: Annotated[int, Field(ge=-1, strict=True)] = -1
    last_error: str | None = None


class CommandReceipt(Record):
    operation: NonEmpty
    request_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    result_type: NonEmpty
    result_id: UUIDString


class PageQuery(DTO):
    limit: Annotated[int, Field(ge=1, le=1000, strict=True)] = 100
    offset: Annotated[int, Field(ge=0, strict=True)] = 0


class MissionQuery(PageQuery):
    pass


class AstronautQuery(PageQuery):
    mission_id: UUIDString | None = None


class TimeQuery(PageQuery):
    from_at: UTCDateTime | None = Field(default=None, alias="from")
    to: UTCDateTime | None = None

    @model_validator(mode="after")
    def window(self):
        if self.from_at is not None and self.to is not None and self.from_at >= self.to:
            raise ValueError("from must precede to")
        return self


class HealthReadingQuery(TimeQuery):
    indicator: HealthIndicator | None = None
    source: Source | None = None
    simulation_run_id: UUIDString | None = None


class EnvironmentalReadingQuery(TimeQuery):
    indicator: EnvironmentalIndicator | None = None
    source: Literal[Source.SIMULATED] | None = None
    simulation_run_id: UUIDString | None = None


class CheckinQuery(TimeQuery):
    pass


class AssessmentQuery(TimeQuery):
    pass


class AlertQuery(PageQuery):
    state: AlertState | None = None


class SimulationRunQuery(PageQuery):
    status: RunStatus | None = None


class Page(DTO, Generic[T]):
    items: list[T]
    total: Annotated[int, Field(ge=0)]
    limit: Annotated[int, Field(ge=1, le=1000)]
    offset: Annotated[int, Field(ge=0)]

    @model_validator(mode="after")
    def size(self):
        if len(self.items) > self.limit or self.total < self.offset + len(self.items) and self.items:
            raise ValueError("page counts inconsistent")
        return self


class ReadinessResult(DTO):
    ready: bool
    adapter: NonEmpty
    detail: str | None = None


class CheckinResult(DTO):
    checkin: DailyCheckin
    readings: list[HealthReading]
    assessment: Assessment
    alerts: list[Alert]


class ReadingBatchResult(DTO):
    readings: list[HealthReading]
    assessment: Assessment
    alerts: list[Alert]


class Dashboard(DTO):
    astronaut: Astronaut
    mission: Mission
    latest_health: list[HealthReading]
    latest_environment: list[EnvironmentalReading]
    checkin: DailyCheckin | None
    assessment: Assessment | None
    alerts: list[Alert]
    simulation_run: SimulationRun | None
    as_of: UTCDateTime


class ErrorDetail(DTO):
    code: NonEmpty
    message: str
    details: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    request_id: UUIDString


class ErrorResponse(DTO):
    error: ErrorDetail


class HealthResponse(DTO):
    status: Literal["ok"] = "ok"
    contract_version: str
    adapter: NonEmpty


class SimulationSteps(DTO):
    steps: Annotated[int, Field(ge=1, le=60, strict=True)]


class SimulationStepResult(DTO):
    run: SimulationRun
    generated_health_count: Annotated[int, Field(ge=0)]
    generated_environmental_count: Annotated[int, Field(ge=0)]


class ScenarioDefinition(DTO):
    scenario: Scenario
    version: NonEmpty
    description: str
    required_fixture_context: list[str]
    expected_outcomes: list[str]


class SourceReference(DTO):
    title: NonEmpty
    url: Annotated[str, Field(pattern=r"^https://")]


class GuidanceArticle(DTO):
    slug: NonEmpty
    title: NonEmpty
    indicators: list[HealthIndicator | EnvironmentalIndicator]
    hazard_slugs: list[str]
    educational_text: str
    limitations: str
    references: list[SourceReference]
    reviewed_on: date


class Hazard(DTO):
    slug: Literal["space_radiation", "isolation_confinement", "distance_from_earth", "gravity_fields", "hostile_closed_environments"]
    title: NonEmpty
    description: str
    related_indicators: list[HealthIndicator | EnvironmentalIndicator]
    monitoring_limitations: str
    references: list[SourceReference]


class HealthTelemetry(DTO):
    astronaut_id: UUIDString
    readings: list[HealthReading]
    as_of: UTCDateTime

    @model_validator(mode="after")
    def simulated_only(self):
        if any(r.source != Source.SIMULATED or r.astronaut_id != self.astronaut_id for r in self.readings):
            raise ValueError("latest simulated telemetry must match astronaut and source")
        return self


class EnvironmentalTelemetry(DTO):
    mission_id: UUIDString
    readings: list[EnvironmentalReading]
    as_of: UTCDateTime

    @model_validator(mode="after")
    def matching_mission(self):
        if any(r.mission_id != self.mission_id for r in self.readings):
            raise ValueError("environmental telemetry must match mission")
        return self
