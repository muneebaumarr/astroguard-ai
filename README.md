# AstroGuard AI

Astronaut health monitoring and educational decision-support prototype.

**Status: Phase 3 explicit fictional telemetry simulator implemented alongside manual check-ins. No real sensor monitoring is active.**

All profiles and measurements are fictional. AstroGuard is not a medical device,
does not diagnose conditions or provide approved mission procedures, and is not
endorsed by NASA or CSA.

## Architecture

React/Vite -> FastAPI services -> shared repository interfaces -> memory or SQLite adapter.

The backend and future database package depend on `astroguard_contracts`.
The database must never import backend modules. Shared contracts contain no ORM models.
The approved REST prefix is `/api/v1`.

The foundation provides six read-only API endpoints, a transactional in-memory
adapter and a responsive React crew workspace backed by actual mission/profile API
responses. Daily Check-In now saves manual observations and shows prior entries and
educational assessments. The overview retrieves saved fictional health and cabin telemetry;
open Mission Simulator to start a run and advance explicit ticks, then return to Overview.
Refresh telemetry reloads saved readings without generating new ones. Backend restarts
clear in-memory data. Advanced history and full
assessment/alert workflows remain unimplemented.

Daily check-ins, limited educational input review and explicit simulated health/cabin
telemetry are implemented. Historical charts, broader assessment/alert workflows and
sourced hazard education remain future work.

## Repository

| Directory | Current purpose | Owner |
|---|---|---|
| frontend | React/Vite/Tailwind workspace, profile selection and component tests | Developer A |
| backend | FastAPI read endpoints, memory adapter, configuration and tests | Developer A |
| database | Teammate handoff and shared dependency declaration; no database code | Developer B |
| shared | Independently installable contracts, fixtures, schemas, examples and tests | Both review; A coordinates |
| docs | Architecture, installation, ownership and exact repository signatures | Both |

## Phase 0 setup

Use **Python 3.13** on both laptops. From repository root in PowerShell:

```powershell
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install -e './shared[test]' -c shared/constraints-py313.txt
.\.venv313\Scripts\python.exe -m pytest shared/tests -q
```

If `py` does not list an installed Python 3.13, invoke the actual 3.13 interpreter
path instead. On this laptop it is:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" -m venv .venv313
```

No activation or execution-policy change is required. Both `.venv` and `.venv313`
have been verified with Python 3.13 on this laptop. Use the environment where you
installed both editable packages. Environments are not committed.

Install only the shared runtime package with `python -m pip install -e ./shared`.
For the running frontend/backend, use the [Phase 1 setup and PowerShell startup instructions](docs/phase1-development.md).
Developer B will add independent database packaging in their implementation phase.

To refresh committed contract examples and schemas after an agreed DTO change:

```powershell
.\.venv313\Scripts\python.exe shared/tools/export_contracts.py
.\.venv313\Scripts\python.exe -m pytest shared/tests -q
```

## Contracts and handoff

- [API contract](shared/api-contract.md)
- [Data dictionary](shared/data-dictionary.md)
- [Representative JSON requests and responses](shared/sample-responses.json)
- [Machine-readable schemas](shared/schema.json)
- [Fictional fixture records](shared/fixtures/fictional.json)
- [Exact repository interface signatures](docs/repository-interfaces.md)
- [Approved architecture and Phase 0 clarifications](docs/architecture.md)
- [Installation, ownership and adapter obligations](docs/development.md)
- [Phase 1 setup, configuration, commands and verification](docs/phase1-development.md)
- [Phase 2 check-ins, API additions, run commands and manual acceptance](docs/phase2-development.md)
- [Phase 3 simulator, endpoints and quick demo](docs/phase3-development.md)

Interfaces are synchronous and expose explicit commit/rollback. Services own IDs,
timestamps and transactions. Adapters return detached DTOs and enforce persistence
constraints. No frontend fetch creates data. Astronaut health readings remain
separate from mission environmental readings.

## Two-developer workflow

| Developer | Responsibilities | Branch |
|---|---|---|
| A | React, FastAPI, memory adapter, simulator, assessments and integration | feature/app |
| B | SQLite, SQLAlchemy, Alembic, database repositories, migrations, seeds and persistence tests | feature/database |

1. Review and merge the Phase 0 contract foundation into `main`.
2. Both developers branch from that shared commit.
3. Work within owned directories and open small reviewed pull requests.
4. Coordinate shared DTO/interface changes before implementation; update examples and tests.
5. Integrate SQLite after the first manual check-in workflow, before complex simulation/dashboard work.
6. Exchange migrations and fixture definitions, never local SQLite files or environments.

Developer B can begin immediately from the shared protocols and deterministic
fixtures without waiting for the frontend. Developer A's foundation and memory
adapter and manual check-in workflow are now implemented. Early SQLite integration
will use Developer B's adapter once it is supplied. Phase 3 is implemented; Phases 4–6 have not started.

## Scientific references

- [NASA: Five Hazards of Human Spaceflight](https://www.nasa.gov/hrp/hazards/)
- [NASA: Risks of Human Spaceflight](https://www.nasa.gov/hrp/risks/)
- [NASA: Ongoing HRP Research](https://www.nasa.gov/hrp/ongoing-hrp-research/)
- [CSA: Monitoring radiation for astronaut health](https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp)

References provide educational context, not approval of demonstration rules or
clinical thresholds. Cabin radiation dose rate is fictional and is not personal dosimetry.
