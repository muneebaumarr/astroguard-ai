# Phase 5: explainable educational assessments and alerts

Ruleset: `educational-demo-v2`. All values, thresholds, profiles, assessments and
alerts are fictional demonstration content. These rules have no clinical validation,
do not diagnose conditions or predict emergencies, and are not NASA/CSA standards.
They do not account for individualized baseline, exercise physiology, sensor error,
exposure duration, medical history or mission procedures. No rule result or resolved
alert is a health/safety clearance. No machine-learning model was added.

## Authored demo rules

| Observation | Review suggested | Crew medical review | Unit |
|---|---|---|---|
| Heart rate | >=110 | >=125 | bpm |
| Oxygen saturation | <=95 | <=92 | % |
| Body temperature | >=37.8 | >=38.5 | degC |
| Cabin CO2 | >=1200 | >=1800 | ppm |
| Cabin radiation dose rate | >=20 | >=35 | uSv/h |
| Sleep duration | <6 | <4 | h |
| Self-reported stress | >=4 | >=5 | scale_1_5 |
| Self-reported mood | <=2 | <=1 | scale_1_5 |
| Reported symptom entry count | >=1 | >=3 | count |

These boundaries were authored solely to make the existing fictional scenarios
demonstrate review workflows; they are **not medical recommendations**. Symptom
count is a demo input flag, not symptom severity. Cabin radiation is not personal
dosimetry. Blood pressure, glucose and exercise activity can remain recorded
observations but have no Phase 5 threshold rules.

Each rule reports triggered, not_triggered or insufficient_data, a human-readable
reason, considered values, units, source record IDs and observation timestamps.
Missing values are omitted, never replaced with zero. Missing required observations
produce insufficient_data. A triggered rule determines the highest supported review
priority. With all rule inputs present and no trigger, status is no_rule_triggered;
that does not mean healthy or safe. A permanent clinical_context result explains the
absence of validated clinical rules, even when the demonstration inputs are complete.

## Integration and transaction behavior

- Daily check-in evaluates only its supplied readings and self-report. Its readings,
  assessment, newly created alerts and command receipt commit together.
- Every explicit simulation tick evaluates its three health and two cabin readings
  in the same UnitOfWork as the generated data. Simulation does not invent sleep,
  stress, mood or symptoms. All ticks in a batch commit or roll back together.
- Explicit Evaluate stored observations uses the latest stored reading per indicator
  across sources, mission cabin readings and the latest check-in by observed_at/id.
  These can be from different times; every timestamp is exposed. No recency or
  physiological correlation is inferred. This command does not advance simulation.
- The input fingerprint is a canonical SHA256 of considered evidence and check-in
  content. Reprocessing identical inputs under this ruleset returns the existing
  immutable assessment without reapplying alert transitions.
- One unresolved alert exists per astronaut/rule. Repeated triggers update its latest
  assessment and review priority, preserving its identity, original opening time and
  acknowledged state. A new evaluated nontrigger resolves it; missing data does not.
  A backdated observation cannot clear or downgrade a flag based on newer evidence.
  After resolution, a new trigger opens a new alert and preserves historical records.
- Acknowledge records awareness only; it preserves evidence and does not resolve the
  alert. Repeated acknowledgement preserves its timestamp; resolved alerts reject new
  acknowledgement commands with 409.
- Existing UUID command keys and optimistic retries remain in effect. Check-in replay
  reconstructs the original **newly created** alert snapshots even after lifecycle
  updates. CheckinResult.alerts contains newly created alerts; GET alerts returns all
  current lifecycle records, including updated existing alerts. Acknowledgement receipt
  operation strings retain assessment ID/priority metadata for exact historical replay;
  no shared DTO or repository signature was changed.
- GET requests only read. No repository evaluates rules or commits independently.

## API additions

All routes already exist in the shared API contract; prefix remains `/api/v1`.

| Method | Path | Result |
|---|---|---|
| POST | /astronauts/{id}/assessments | Assessment, HTTP 200, no request body |
| GET | /astronauts/{id}/alerts | Page[Alert], optional state/limit/offset |
| POST | /astronauts/{id}/alerts/{alert_id}/acknowledgement | Alert, HTTP 200, no body |

Both POST endpoints require UUID `Idempotency-Key`. Existing GET assessment list/detail
and check-in/simulation response schemas are preserved. Alert state and priorities
use existing enum values; no low/medium/high severity field or new API schema exists.
The database module and all shared contracts remain unchanged.

## Frontend

Assessments & Alerts replaces the placeholder with latest/selected assessment,
rule explanations, evidence values/units/timestamps, missing context, history,
recent alerts, review-priority badges and acknowledgement. Alert links open the
relevant assessment for the selected astronaut. Evaluate/refresh use real FastAPI
requests; uncertain POSTs can retry the same key. Loading, errors and empty states
are explicit. Requests are aborted and stale responses ignored on crew changes.
Overview includes up to four recent alerts, refreshes them after every saved tick
and links to the full explanation. Existing daily check-in and simulator interfaces
remain available. Clinical interpretation and sourced guidance remain outside scope.

## Files changed for Phase 5

- `backend/app/services/initial_assessment.py`: pure deterministic rules and fingerprints.
- `backend/app/services/assessments.py` (new): assessment persistence, alert lifecycle,
  explicit evaluation, acknowledgement, replay and transaction retry orchestration.
- `backend/app/services/checkins.py`: atomic assessment/alert creation and exact replay.
- `backend/app/services/simulation.py`: atomic evaluation of each explicit tick.
- `backend/app/api/v1/checkins.py`: contract-defined evaluation and alert endpoints.
- `backend/tests/test_assessments.py` (new): rule, lifecycle and transaction regressions.
- `backend/tests/test_checkins.py`: complete Phase 5 missing-rule coverage expectation.
- `backend/tests/test_api.py`: new contract-defined paths in exact OpenAPI assertion.
- `frontend/src/pages/Assessments.jsx` (new): full assessment/alert workspace.
- `frontend/src/components/common/AssessmentDetails.jsx` (new): evidence/alert components.
- `frontend/src/app/App.jsx`, `frontend/src/app/navigation.js`: functional workspace route.
- `frontend/src/services/api.js`: alert reads, evaluation and acknowledgement commands.
- `frontend/src/hooks/useLiveDashboard.js`, `frontend/src/pages/Dashboard.jsx`: live alerts.
- `frontend/src/styles/global.css`: responsive assessment and priority presentation.
- `frontend/tests/Assessments.test.jsx` (new): workspace rendering, errors, retry and isolation.
- `frontend/tests/App.test.jsx`, `frontend/tests/Dashboard.test.jsx`: navigation and Overview.
- `README.md`, `docs/phase5-development.md` (new): status, rules and operating instructions.

## Run and manual acceptance

From repository root, start one backend only:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

From another terminal:

```powershell
cd frontend
npm.cmd run dev
```

1. Open http://127.0.0.1:5173/. Choose a fictional astronaut.
2. On Daily Check-In, save fictional heart rate **130 bpm** and a fictional symptom
   on an unused UTC date. Confirm the saved assessment has an explained review flag.
3. Open Assessments & Alerts. Inspect each reason, source timestamp, numeric value and
   unit. Confirm crew_medical_review and review_suggested are labelled as demo priorities.
4. Acknowledge an open alert. Confirm timestamp and acknowledged state. Refresh the
   browser and verify the record persists while the same backend process runs.
5. Save a later-dated fictional heart rate **72 bpm**. The heart-rate demo alert
   resolves; a symptom flag remains until symptoms are evaluated again as not triggered.
   A notes-only submission must not clear a flag whose required measurement is missing.
6. On Overview, stop any existing run, select environmental_change, Start, then Play.
   Cabin review flags appear after several ticks and update without duplicate active
   alerts. Pause and inspect Recent alerts, then follow Supporting assessment.
7. Switch astronauts. Assessments and alerts from the previous astronaut must disappear.
   Mission cabin readings can be shared context when explicitly evaluating that mission.
8. Stop the backend temporarily and refresh: confirm a useful error, then restart and
   refresh. Restart clears runtime memory. Never present this as durable storage.

## Verification and limitations

Run `python -m pytest shared/tests backend/tests -v` from root with the project venv.
Run `npm.cmd test -- --run` and `npm.cmd run build` from frontend.
Tests cover deterministic boundaries, values/units, explanations, no fabricated data,
atomic failures, lifecycle/duplicates, original response replay, astronaut isolation,
frontend priority/evidence display, error/retry, navigation and Overview integration.

Final verification: **201 Python tests passed**, **69 frontend tests passed**, and
**production build passed**. This includes 24 new backend cases and nine new frontend
cases. Existing exact endpoint/coverage assertions were updated for the Phase 5
functionality; earlier test coverage was preserved. The main bundle is approximately
689 kB minified / 205 kB gzipped, producing the existing nonfatal chunk warning.

This is an authored educational demo with process-local storage and no background
assessment worker. Reads never refresh evaluations automatically; they show committed
results. SQLite integration, validated medical rules, intervention guidance, durable
audit storage and real sensor ingestion are not implemented here. Recharts still
causes a nonfatal production chunk-size warning. UI tests use jsdom and mocked API
responses; they do not claim a manual browser walkthrough.
