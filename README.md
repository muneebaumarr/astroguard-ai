# AstroGuard AI

Astronaut health monitoring and educational decision-support prototype.

**Status: Phase 0 shared contracts complete. Application features are not implemented.**

All profiles and measurements are fictional. AstroGuard is not a medical device,
does not diagnose conditions or provide approved mission procedures, and is not
endorsed by NASA or CSA.

## Architecture

React/Vite -> FastAPI services -> shared repository interfaces -> memory or SQLite adapter.

The backend and future database package depend on `astroguard_contracts`.
The database must never import backend modules. Shared contracts contain no ORM models.
The approved REST prefix is `/api/v1`.

Planned features include daily check-ins, simulated health and cabin telemetry,
history charts, explainable demonstration assessments, alerts and sourced education
about NASA's five spaceflight hazards. All remain future implementation work.

## Repository

| Directory | Current purpose | Owner |
|---|---|---|
| frontend | Boundary documentation; React begins in Phase 1 | Developer A |
| backend | Boundary documentation and shared dependency declaration | Developer A |
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

No activation or execution-policy change is required. The earlier `.venv` uses
Python 3.15; use `.venv313` for this project. Environments are not committed.

Install only the shared runtime package with `python -m pip install -e ./shared`.
Backend/database requirement files reference that installed distribution. They do
not currently install or start an application. Developer B will add independent
database packaging in their implementation phase.

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
fixtures without waiting for the frontend. Developer A's next step is the application
foundation and memory adapter, followed by the first check-in workflow. Neither
step is included in Phase 0.

## Scientific references

- [NASA: Five Hazards of Human Spaceflight](https://www.nasa.gov/hrp/hazards/)
- [NASA: Risks of Human Spaceflight](https://www.nasa.gov/hrp/risks/)
- [NASA: Ongoing HRP Research](https://www.nasa.gov/hrp/ongoing-hrp-research/)
- [CSA: Monitoring radiation for astronaut health](https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp)

References provide educational context, not approval of demonstration rules or
clinical thresholds. Cabin radiation dose rate is fictional and is not personal dosimetry.
