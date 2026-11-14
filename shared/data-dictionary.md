# Data dictionary

Authoritative structural types: astroguard_contracts.dto and enums. schema.json
contains complete JSON schemas (including required lists and field constraints).
No clinical threshold is asserted by any validation range.

## Common fields and types

Record: id (canonical UUID string), created_at (UTC timestamp), both required.
UUID references are strings; no ORM objects. UTCDateTime rejects naive input and
normalizes offsets. FiniteFloat rejects NaN/infinity. Unknown fields are rejected.
Domain records are detached DTO snapshots; consumers must not mutate nested lists.
is_demo is always true on missions, astronauts and observations.

## Entities

| DTO / table | Fields beyond Record | Storage constraints |
|---|---|---|
| Mission / missions | name:string, environment:enum, started_at:UTC, ended_at:UTC?=null, description:string="", is_demo:true | end > start |
| Astronaut / astronauts | mission_id:UUID, display_name:string, role:string, is_demo:true | FK mission; index mission_id |
| DailyCheckin / daily_checkins | astronaut_id:UUID, checkin_date:date, observed_at:UTC, context:enum, readings:HealthValue[]=[], sleep_hours:float?=null, mood:int?=null, stress:int?=null, symptoms:string[]=[], exercise_minutes:int?=null, notes:string?=null, is_demo:true | FK astronaut; unique astronaut/date; index astronaut/observed_at; readings reconstructed |
| HealthReading / health_readings | astronaut_id:UUID, indicator:health enum, value:float, unit:enum, observed_at:UTC, source:enum, context:enum, checkin_id:UUID?=null, simulation_run_id:UUID?=null, tick_index:int?=null, is_demo:true | FKs astronaut/checkin/run; index astronaut/indicator/observed_at/id; unique run/tick/indicator for simulation |
| EnvironmentalReading / environmental_readings | mission_id:UUID, indicator:environment enum, value:float, unit:enum, observed_at:UTC, source:simulated, simulation_run_id:UUID, tick_index:int, is_demo:true | FKs mission/run; index mission/indicator/observed_at/id; unique run/tick/indicator |
| Assessment / assessments | astronaut_id:UUID, evaluated_at:UTC, status:enum, ruleset_version:string, input_fingerprint:SHA256 hex, coverage:Coverage, results:RuleResult[] | FK astronaut; unique astronaut/ruleset/fingerprint; index astronaut/evaluated_at |
| Alert / alerts | astronaut_id:UUID, rule_id:string, workflow_status:review enum, state:enum, first_assessment_id:UUID, latest_assessment_id:UUID, opened_at:UTC, acknowledged_at:UTC?=null, resolved_at:UTC?=null | FKs astronaut/assessments; unique active astronaut/rule; index astronaut/state |
| SimulationRun / simulation_runs | astronaut_id:UUID, mission_id:UUID, scenario:enum, seed:int, simulation_start_at:UTC, interval_seconds:int=5, step_seconds:int=60, scenario_version:string, status:enum=paused, started_at:UTC?=null, last_tick_index:int=-1, last_error:string?=null | FKs astronaut/mission; mission must match astronaut; only one paused/running globally |
| CommandReceipt / command_receipts | operation:string, request_hash:SHA256 hex, result_type:string, result_id:UUID | id is client command UUID; result_id is polymorphic, checked by service |

Nonempty short strings are limited to 200 characters. Description/text fields are
ordinary strings. Primary keys/required fields cannot be null. Optional fields above
default to null; all other fields without explicit defaults are required.

## Indicator units and source metadata

| Health indicator | Unit |
|---|---|
| heart_rate | bpm |
| blood_pressure_systolic | mmHg |
| blood_pressure_diastolic | mmHg |
| blood_glucose | mg/dL |
| body_temperature | degC |
| spo2 | % |

| Environment indicator | Unit |
|---|---|
| cabin_co2 | ppm |
| radiation_dose_rate | uSv/h |

Environment radiation is fictional cabin dose rate, not a personal dose estimate.
Non-temperature values are nonnegative; SpO2 is 0..100. No clinical ranges apply.
Blood pressure batch/check-in values must include both components; systolic > diastolic.
No duplicate indicator in a batch. Health readings source: manual or simulated.
Manual records cannot carry run/tick metadata. Simulated records require both and
cannot link to a manual check-in. Environment source is simulated only.

Sleep: 0..24 h; mood: integer 1..5 (higher more positive); stress: integer 1..5
(higher more stress); exercise: integer 0..1440 min. Check-in requires at least one
observation, and checkin_date must match observed_at's UTC date. Symptoms: at most
20 strings, each 1..100 characters; notes at most 2000 characters. Zero is data.

## Enums

- Environment: microgravity, lunar, martian, earth_analog.
- Context: resting, exercise, recovery, unspecified.
- Assessment status: insufficient_data, no_rule_triggered, review_suggested, crew_medical_review.
- Rule outcome: triggered, not_triggered, insufficient_data, not_applicable.
- Alert state: open, acknowledged, resolved. workflow_status is review_suggested or crew_medical_review.
- Run state: paused, running, stopped, failed.
- Scenario: routine, exercise_recovery, reduced_sleep_stress, unusual_health_trend, environmental_change.

## Supporting schemas

- HealthValue: indicator, value, unit.
- Coverage: evaluated_rule_ids, insufficient_rule_ids, not_applicable_rule_ids; lists default empty.
- Evidence: record_id, record_type (health_reading/environmental_reading/daily_checkin),
  observed_at, indicator, value, unit. Self-report units may be h, min or scale_1_5.
- RuleResult: rule_id, outcome, workflow_status, explanation; evidence, missing_data,
  guidance_slugs default empty. Values explain a demo workflow, never a diagnosis.
- MissionCreate/AstronautCreate: corresponding record fields without Record/is_demo.
- CheckinCreate: DailyCheckin fields without Record/astronaut_id/is_demo.
- ManualReadingBatch: observed_at, context, nonempty readings:HealthValue[].
- SimulationRunCreate: astronaut_id, scenario, seed, simulation_start_at, interval_seconds,
  step_seconds. Interval 1..60; step 1..3600; seed is an integer.
- SimulationSteps: steps integer 1..60. SimulationStepResult: run and generated health/environmental counts.
- CheckinResult: checkin, readings, assessment, alerts. ReadingBatchResult omits checkin.
- Dashboard: astronaut, mission, latest_health, latest_environment, nullable checkin,
  nullable assessment, alerts, nullable simulation_run, as_of.
- HealthTelemetry: astronaut_id, readings (simulated only), as_of.
- EnvironmentalTelemetry: mission_id, readings, as_of.
- HealthResponse: status=ok, contract_version, adapter. ReadinessResult: ready, adapter, detail?=null.
- ErrorResponse wraps ErrorDetail: code, message, details (flat scalar map), request_id.
- SourceReference: title, HTTPS url. GuidanceArticle: slug, title, indicators,
  hazard_slugs, educational_text, limitations, references, reviewed_on.
- Hazard: fixed NASA-category slug, title, description, related_indicators,
  monitoring_limitations, references.
- ScenarioDefinition: scenario, version, description, required_fixture_context, expected_outcomes.

## Adapter-only invariants

DTOs validate single-record structure. Adapters/services also enforce parent existence,
matching astronaut/mission/check-in ownership, unique daily entries, fingerprint dedupe,
global active run uniqueness, command idempotency and active alert uniqueness. These
cannot be established from an isolated DTO. Store vital readings once; reconstruct
DailyCheckin.readings via checkin_id. Never cascade-delete history. Alert timestamps
cannot precede opening; acknowledged/resolved timestamps must agree with state.

Fixture namespace and stable IDs are defined in astroguard_contracts.fixtures. They
use fixed UTC dates, never the current clock. Fixture functions return fresh values;
they neither open a database nor simulate new readings.
