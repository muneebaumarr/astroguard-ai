# Phase 3: explicit fictional telemetry simulator

## Run locally

From repository root in PowerShell (Python 3.13, existing editable packages):

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd C:\Users\WIN-X\astroguard-ai\frontend
npm.cmd run dev
```

Open http://127.0.0.1:5173/demo or choose Mission Simulator in the sidebar.
API documentation: http://127.0.0.1:8000/docs. No new dependencies are required.
Use one backend worker without --reload for a stable in-memory demonstration.

## Quick demonstration

1. Select Maya Demo. A pre-existing paused fictional fixture run may be loaded.
   Stop that run to free the globally active slot before creating a new scenario.
2. Choose a scenario, seed 42 and a UTC simulation start. Click Start simulation.
   This creates a paused run without readings. There is no automatic timer.
3. Click Advance one tick. Inspect heart rate (bpm), oxygen saturation (%), body
   temperature (degC), cabin CO2 (ppm) and cabin radiation dose rate (uSv/h).
4. Advance again; simulated time advances 60 seconds. Refresh the browser: stored
   run state and selected-run readings return without advancing another tick.
5. Stop the run. Repeat with the same scenario, seed and start time: generated
   observed values/timestamps repeat for the same tick indices. Try environmental
   change or exercise/recovery to demonstrate different authored patterns.
6. Switch astronauts: prior health readings must not appear under the new profile.
   If another profile has the active run, select that profile and stop it first.

## Endpoints added (all under /api/v1)

| Method | Path | Shared response |
|---|---|---|
| GET | /simulation/scenarios | Page[ScenarioDefinition] |
| GET | /simulation/runs | Page[SimulationRun] |
| POST | /simulation/runs | SimulationRun (201) |
| GET | /simulation/runs/{id} | SimulationRun |
| POST | /simulation/runs/{id}/steps | SimulationStepResult |
| POST | /simulation/runs/{id}/pause | SimulationRun |
| POST | /simulation/runs/{id}/resume | SimulationRun |
| POST | /simulation/runs/{id}/stop | SimulationRun |
| GET | /astronauts/{id}/telemetry/latest | HealthTelemetry |
| GET | /missions/{id}/telemetry/latest | EnvironmentalTelemetry |
| GET | /missions/{id}/environmental-readings | Page[EnvironmentalReading] |

Existing GET /astronauts/{id}/readings supports source and simulation_run_id filters.
Environmental history uses the existing limit/offset, from/to, indicator, source and
simulation_run_id query conventions. Runs support the existing status query. GETs
never generate or persist data. No custom DTO, repository method or API path was added.

## Determinism and atomicity

The pure generator hashes version/scenario/seed/tick/indicator using SHA256, not
Python's randomized hash or wall-clock randomness. It supports routine,
exercise_recovery, reduced_sleep_stress, unusual_health_trend and environmental_change.
Patterns are bounded and authored solely for fictional demonstration, with no
medical classification. The sleep/stress scenario does not infer or write self-reports.

Observed time is simulation_start_at + tick_index * step_seconds. The first new-run
tick is index 0; last_tick_index starts at -1. UUID5 identities derive from run/tick/
indicator, preventing duplicate reading identities. New runs use telemetry-v1; demo-v1
is supported to allow advancing the unchanged legacy fixture run. Its original seeded
tick is an authored fixture, not output from this generator.

A steps command generates 3 health plus 2 environmental readings per tick. Readings,
run progress and its CommandReceipt commit together through existing UnitOfWork.
Failure rolls back every write. Optimistic concurrency conflicts retry a fresh snapshot
up to three times. No assessments, alerts, charts or guidance are produced by ticks.

## Lifecycle and command replay

Create returns paused and generates nothing. Steps accepts the shared 1..60 count,
only for paused runs. Stop is terminal; pause/resume are also exposed as contracted
state controls. **Per the Phase 3 request, even running state has no background loop.**
Pause before explicit steps. interval_seconds remains a validated configuration field
but does not schedule work. The UI uses create/steps/stop (and pause for a run resumed
through an API client), making generation entirely deliberate.

Only one paused/running run is allowed globally, including the pre-seeded fixture.
The UI shows that constraint rather than silently deleting or replacing another run.

All mutations require a UUID Idempotency-Key. Canonical command hashes include action,
target and payload. Same key/command replays the original response; changed commands
with that key return 409. Exact replay remains correct after later ticks or stopping.
The existing free-text CommandReceipt.operation field holds the action plus a compact
JSON tuple of tick/status/started_at, and result_id references the run. Immutable run
configuration plus this revision metadata reconstructs the original shared response.
This uses existing validated fields; no response cache, schema or SQLite work was added.
created_at is an audit timestamp, so it and run/reading IDs differ across separate runs;
deterministic sensor values and observed timestamps do not depend on it.

The frontend reuses keys on failed-command retries, including the original button,
blocks double clicks and aborts/ignores stale requests on astronaut switches. Selected
run IDs are retained per astronaut in tab storage; values are always fetched from the
API. The page filters telemetry to the selected run, avoiding mixed-run cabin data.
Latest telemetry API endpoints separately return latest-by-observation records across
the requested astronaut/mission, as specified by the shared repository contracts.

## Verification and limits

```powershell
.\.venv\Scripts\python.exe -m pytest shared/tests backend/tests -q
cd frontend
npm.cmd test -- --run
npm.cmd run build
```

177 Python tests passed (79 shared and 98 backend), including 24 new simulation
cases. 45 frontend tests passed, including 9 new simulator cases. The production
build and pip check passed. The live HTTP smoke demo created/stopped runs, advanced
ticks, retrieved 3+2 readings, replayed without duplicates, and reproduced values
across two equivalent runs. Vite /demo returned HTTP 200. A visual browser inspection
was not performed for this delivery.

Memory survives browser refresh only while the same backend process runs. Restart,
Python development reload or a different worker resets/isolates memory. No durable
database adapter, database seed or migration was implemented. Shared contracts and
database/ remain unchanged. Phases 4–6 were not started. Nothing was committed/pushed.
