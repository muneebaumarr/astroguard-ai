# AstroGuard API contract 0.1.0

Base path: `/api/v1`. This document specifies future routes; Phase 0 contains no server.
Python schema authority: astroguard_contracts.dto. JSON examples: sample-responses.json.
All observations are fictional. Never present these workflow labels as diagnoses.

## HTTP conventions

- UUIDs are lowercase hyphenated strings. Timestamps require a timezone and serialize
  normalized UTC with Z. Field names use snake_case.
- POST requires an Idempotency-Key UUID. Store a canonical payload hash and receipt
  in the same transaction as effects. Equal command replay returns the original
  resource/status; changed operation/payload returns 409. Receipts persist for MVP.
- Created resources return 201; evaluation, acknowledgement, controls and steps 200.
- GET is read-only. Only POST commands generate or evaluate new data.
- Collection schema Page[T]: items, total, limit (default 100/max 1000), offset (default 0).
- TimeQuery uses wire keys `from` (inclusive) and `to` (exclusive); from_at is its
  Python attribute. History uses observed_at ascending then id ascending. Assessment
  history uses evaluated_at descending then id descending; alerts opened_at/id descending.
- Reading filters: indicator, source, simulation_run_id, from, to, limit, offset.
- Astronaut list supports mission_id. Alerts support state; runs support status.
- A missing or unrelated nested resource returns 404.

## Endpoints (relative to base path)

| Method | Path | Request | Response |
|---|---|---|---|
| GET | /health | none | HealthResponse |
| GET | /ready | none | ReadinessResult (503 if not ready) |
| GET | /missions | MissionQuery | Page[Mission] |
| POST | /missions | MissionCreate | Mission |
| GET | /missions/{id} | none | Mission |
| GET | /astronauts | AstronautQuery | Page[Astronaut] |
| POST | /astronauts | AstronautCreate | Astronaut |
| GET | /astronauts/{id} | none | Astronaut |
| GET | /astronauts/{id}/readings | HealthReadingQuery | Page[HealthReading] |
| POST | /astronauts/{id}/readings | ManualReadingBatch | ReadingBatchResult |
| GET | /astronauts/{id}/checkins | CheckinQuery | Page[DailyCheckin] |
| POST | /astronauts/{id}/checkins | CheckinCreate | CheckinResult |
| GET | /astronauts/{id}/assessments | AssessmentQuery | Page[Assessment] |
| POST | /astronauts/{id}/assessments | no body; evaluate stored data | Assessment |
| GET | /astronauts/{id}/assessments/{assessment_id} | none | Assessment |
| GET | /astronauts/{id}/alerts | AlertQuery | Page[Alert] |
| POST | /astronauts/{id}/alerts/{alert_id}/acknowledgement | no body | Alert |
| GET | /astronauts/{id}/dashboard | none | Dashboard |
| GET | /astronauts/{id}/telemetry/latest | none | HealthTelemetry |
| GET | /missions/{id}/environmental-readings | EnvironmentalReadingQuery | Page[EnvironmentalReading] |
| GET | /missions/{id}/telemetry/latest | none | EnvironmentalTelemetry |
| GET | /simulation/scenarios | PageQuery | Page[ScenarioDefinition] |
| GET | /simulation/runs | SimulationRunQuery | Page[SimulationRun] |
| POST | /simulation/runs | SimulationRunCreate | SimulationRun (paused, no data generated) |
| GET | /simulation/runs/{id} | none | SimulationRun |
| POST | /simulation/runs/{id}/pause | no body | SimulationRun |
| POST | /simulation/runs/{id}/resume | no body | SimulationRun |
| POST | /simulation/runs/{id}/stop | no body | SimulationRun |
| POST | /simulation/runs/{id}/steps | SimulationSteps | SimulationStepResult |
| GET | /guidance | PageQuery; optional indicator/hazard | Page[GuidanceArticle] |
| GET | /guidance/{slug} | none | GuidanceArticle |
| GET | /hazards | PageQuery | Page[Hazard] |
| GET | /hazards/{slug} | none | Hazard |

## Request and response schemas

All DTO fields, required flags, enum values and structural constraints are described
in data-dictionary.md and generated schema.json. Unknown fields are rejected.
Create requests omit server IDs, created_at, source lineage and fictional profile flags.
CheckinCreate.readings is a list of HealthValue objects; saved DailyCheckin reconstructs
that list from linked health_readings. CheckinResult additionally includes those full
reading records, assessment and alerts for the atomic workflow.

Missing measurements are omitted or null, never replaced with zero. No check-in edit
endpoint exists. Duplicate astronaut/date returns 409; check-in date is UTC.
ManualReadingBatch allows only health indicators. Environmental records are generated
by simulation and belong to a mission, never an astronaut.

Dashboard.as_of describes the snapshot, not observation freshness. latest_health
contains the newest stored value per indicator across sources; latest simulated
telemetry contains only simulated records. Empty telemetry returns an empty readings
array. Nullable checkin/assessment/run represent no available record. Dashboard alerts
include open and acknowledged unresolved alerts.

State controls: pause/resume only nonterminal runs; repeated pause/resume in the same
state is harmless. Stop on stopped is harmless; failed and stopped cannot resume.
Explicit steps require paused run and steps 1..60. Only one running/paused run globally.
No frontend GET triggers ticks. Acknowledging a resolved alert is a 409; repeated
acknowledgement preserves its timestamp. Acknowledgement never clears medical evidence.

## Error responses

ErrorResponse = {error: {code, message, details, request_id}}.
details is a flat field-to-scalar map, allowing forms to associate validation messages.
Codes: not_found (404), conflict/invalid_transition/idempotency_conflict (409),
validation_error (422), repository_unavailable (503), internal_error (500).
Do not expose stack traces, SQL, credentials or raw exception internals.

## Repository semantics

Exact synchronous signatures live in src/astroguard_contracts/repositories.py.
Every unit of work exposes all nine repositories. Exit never suppresses errors;
uncommitted work rolls back, including partial add_many writes. Methods return
detached DTOs; storage adapters must not evaluate health rules or invent timestamps.
The service supplies IDs/timestamps and owns commits. get returns None when absent;
list returns a typed page. get_active includes paused/running; get_open includes
acknowledged/unresolved alerts. Latest ties use the greatest observed_at then id.
update(run, expected_last_tick) checks stored progress before replacing it, raising
ConcurrentWrite on mismatch. Uniqueness violations raise Conflict.
