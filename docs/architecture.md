# Approved architecture and Phase 0 decisions

AstroGuard is a local fictional educational prototype, not a medical device.
The approved architecture uses React/Vite, FastAPI/Pydantic v2, and SQLite with
SQLAlchemy 2.x/Alembic. Python 3.13 is the common development runtime.

Dependency direction: backend -> astroguard_contracts <- astroguard_db.
The backend selects an injected memory or database adapter. Routes call services;
services coordinate transactions; repositories return detached shared DTOs.
No ORM or backend imports belong in the shared package or database-to-backend boundary.

## Approved behavior for later phases

- API prefix /api/v1; GET never generates records.
- Atomic check-in + readings + assessment + alerts + command receipt.
- Single backend process and globally one active (running or paused) simulation.
- Paused run creation; resume begins generation; stop/failed are terminal.
- Deterministic simulation uses seed, scenario version, indicator and tick index.
- Stable tick IDs and unique run/tick/indicator constraints prevent duplicate writes.
- Simulation interval defaults to 5 real seconds, step to 60 simulated seconds.
- Restart pauses any running simulation; no catch-up generation.
- Poll dashboard/run every 5 seconds and visible history every 15 seconds.
- Separate astronaut observations from mission cabin measurements. Radiation is
  cabin dose rate in uSv/h, never inferred personal exposure.
- Assessments use versioned synthetic demo rules with explicit evidence coverage.
- Missing data never means reassuring data. Statuses are workflow labels, not diagnoses.
- Alerts acknowledge awareness; only subsequent evaluable non-triggering evidence
  resolves a pattern. Missing evidence leaves the alert open.
- Guidance is bundled with NASA/CSA citations. No runtime external AI service.

## Development order

0. Shared contracts and repository foundation (this delivery).
1. App foundation and in-memory adapter (A); database foundation in parallel (B).
2. Profiles and check-ins, then early SQLite integration.
3. Persisted simulator and explicit controls.
4. Dashboard and history.
5. Explainable assessments and alerts.
6. Guidance and hazard explorer.
7. Complete persistence acceptance (integration starts earlier, not at the end).
8. Accessibility, failure handling, testing and reproducible demo.

First vertical slice: select fictional astronaut, submit a check-in, inspect saved
values and assessment, refresh and restart to confirm SQLite persistence.

## Phase 0 clarifications

- Architecture abbreviations are completed with named query DTOs and typed returns;
  method names and argument order are unchanged.
- DailyCheckin is a reconstructed DTO containing vital values. Database storage
  persists those values only in linked health_readings, not a second vital column set.
- SimulationRun.started_at is nullable because a newly created paused run has never
  started. last_tick_index starts at -1; tick 0 is the first generated tick.
- Acknowledged alerts remain active for get_open and open-alert uniqueness.
- Evidence contains typed numeric observations, not arbitrary ORM/JSON objects.
- UTC-aware input offsets normalize to UTC; naive timestamps are rejected.
- Backend/database requirements declare their shared dependency; their installable
  implementations and runtime dependencies remain with their respective owners.

No React, FastAPI routes, memory/SQLite adapters, seeds that write a database,
simulator, assessment evaluator or migration is implemented in Phase 0.
