# Phase 1 local development

Phase 1 provides the frontend/backend foundation only. It does not implement
check-in submission, assessments, alerts, simulation, history retrieval or SQLite.
Use the feature/app branch. Developer B's database directory and all shared
contracts remain unchanged.

## Requirements and installation

Python 3.13 and a current Node.js LTS release (22.12+ or newer supported LTS) with
npm. This laptop was verified with Python 3.13.17 and Node 26.13.1/npm 11.20.0.
Use the same package-lock.json with npm ci; do not copy node_modules between laptops.

Run from C:\Users\WIN-X\astroguard-ai in PowerShell (adjust checkout path on teammate's laptop):

```powershell
git branch --show-current
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install -e './shared[test]' -e './backend[test]' -c backend/constraints-py313.txt
cd frontend
npm.cmd ci
```

If py cannot detect the existing runtime on this laptop, replace only the venv
creation command with:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" -m venv .venv313
```

Use an explicitly verified Python 3.13 interpreter. Both .venv313 and the repaired
.venv on this laptop now use Python 3.13; install the editable packages into whichever
environment you use. No activation or execution-policy change is needed.

## Start locally

Backend terminal, from repository root:

```powershell
.\.venv313\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend terminal:

```powershell
cd C:\Users\WIN-X\astroguard-ai\frontend
npm.cmd run dev
```

Use one backend process. Stop each server with Ctrl+C. Vite uses strictPort so an
occupied 5173 fails rather than silently switching to an unexpected origin.

| URL | Expected behavior |
|---|---|
| http://127.0.0.1:5173/ | API-backed crew overview; measurements show No data |
| http://127.0.0.1:5173/mission | Fictional mission and selectable crew |
| http://127.0.0.1:5173/check-in | Honest placeholder; no submission form |
| http://127.0.0.1:8000/api/v1/health | status ok, contract version, memory adapter |
| http://127.0.0.1:8000/api/v1/ready | repository ready |
| http://127.0.0.1:8000/api/v1/missions | Fixture mission in Page[Mission] |
| http://127.0.0.1:8000/api/v1/astronauts | Two fixture astronauts in Page[Astronaut] |
| http://127.0.0.1:8000/docs | OpenAPI for exactly the six approved read endpoints |

The UI never substitutes mock profiles after failed requests. Retry reconnects to
the actual API. It follows pagination and aborts/ignores stale selection requests.

## Configuration

Backend reads backend/.env then environment variables, with environment taking
precedence. Frontend uses Vite's frontend/.env convention. Both work with their
documented defaults without creating .env files. Copy the corresponding .env.example
only when configuring overrides; secrets and environment files remain ignored.

| Setting | Default |
|---|---|
| REPOSITORY_BACKEND | memory |
| CORS_ORIGINS | http://127.0.0.1:5173,http://localhost:5173 (comma-separated) |
| VITE_API_BASE_URL | http://127.0.0.1:8000 (origin only, no /api/v1 suffix) |

Selecting sqlite or an unknown adapter fails startup explicitly. No fallback is
implemented. Developer B's adapter integration is future work. Missing readiness
returns shared ReadinessResult with HTTP 503; ordinary failures use ErrorResponse.
All requests include a generated X-Request-ID. Validation uses flat field messages.

## Memory adapter semantics

The factory holds only process-local state. It loads the unchanged shared fixture
bundle, including historical sample records, but this phase exposes only missions
and astronauts. A new application lifespan reloads the original fixtures.

Each UnitOfWork creates an isolated deep snapshot. Methods are synchronous and
return detached DTOs. Explicit commit validates foreign keys, cross-record ownership,
daily uniqueness, fingerprint uniqueness, active alert/run uniqueness and tick
uniqueness before atomically replacing state. Uncommitted exits/exceptions roll back.
After a successful commit, subsequent uncommitted changes can still be rolled back.

Optimistic store revisions prevent lost concurrent writes; stale commits and stale
run progress raise ConcurrentWrite. Callers must open a new transaction/re-read after
such a conflict. Repository methods never auto-commit. Constraint checks spanning
multiple tables are deferred to commit so future atomic workflows can stage all their
records together. This is a temporary adapter, not durable storage or a clinical system.

Injected adapter factories are caller-owned; the app closes only a factory it creates.
Startup initializes the factory in lifespan and shutdown closes its memory resource.
No background monitoring task is started.

## Verification

The root pytest.ini runs both suites with warnings treated as errors and disables
pytest's optional cache provider. This avoids Windows Access Denied errors from
previously created cache folders without changing folder permissions or contracts.
The root conftest.py also gives each run a fresh temporary directory, avoiding
permission errors in an old Windows Temp/pytest-of-<user> folder. It cleans up only
its own temporary directory and respects an explicit --basetemp argument.

If your active environment is named .venv rather than .venv313, verify it is Python
3.13, then install both local packages and the same dependency constraints into that
environment. Installing them into .venv313 does not install them into .venv:

```powershell
python --version
python -m pip install -e './shared[test]' -e './backend[test]' -c backend/constraints-py313.txt
python -m pip check
python -m pytest shared/tests backend/tests -v
```

From repository root:

```powershell
.\.venv313\Scripts\python.exe -m pytest shared/tests -q
.\.venv313\Scripts\python.exe -m pytest backend/tests -q
.\.venv313\Scripts\python.exe -m pip check
cd frontend
npm.cmd test
npm.cmd run build
```

Tests cover read endpoints, exact fixture profiles, response schemas, errors,
pagination, filtering, CORS, startup/shutdown, no GET side effects, memory reset,
commit/rollback, concurrent writes, atomic failure, detached DTOs and protocol
signatures. Frontend tests cover rendering, navigation, real-client call paths,
selection, delayed-response races, retry, unavailable/empty/loading states and labels.
Component tests use controlled HTTP responses; the live local browser check uses
the actual backend and no fixture fallback in frontend code.

The backend bounds Starlette below 1 for the agreed HTTPX test client and AnyIO below
4.12 for compatibility with that Starlette release. Exact verified versions are in
backend/constraints-py313.txt; shared constraints were not changed. Vitest/Vite tooling
was updated together to resolve installation advisories; npm install reported zero
vulnerabilities after the update. Tailwind uses @tailwindcss/vite and CSS @import.

## Next phase (not implemented)

Developer A: validated manual check-in form, API workflow and atomic persistence
through UnitOfWork, followed by early integration with Developer B's adapter.
Developer B retains exclusive ownership of SQLAlchemy, SQLite, Alembic, migrations,
database packaging, database seeds and persistence tests.
