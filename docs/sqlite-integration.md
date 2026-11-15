# SQLite integration and cutover

FastAPI now selects Developer B's independent `astroguard_db.SqliteAdapterFactory`
when `REPOSITORY_BACKEND=sqlite`. The optional memory adapter remains available.
Shared contracts, DTOs, API paths and the existing Alembic migration are unchanged.

## Local setup (PowerShell, Python 3.13)

Run from repository root with an existing .venv:

```powershell
.\.venv\Scripts\python.exe -m pip install -e './shared[test]' -e './database[test]' -e './backend[sqlite,test]'
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
.\.venv\Scripts\python.exe -m app.prepare_database --seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

The supplied backend/.env.example selects SQLite. On this laptop a Git-ignored
backend/.env is configured for SQLite. Existing custom configuration should be
edited deliberately rather than overwritten. Environment variables take precedence
over backend/.env. `Settings()` defaults to memory for explicit tests and embeddings;
normal app launch uses `Settings.from_env()`.

Default database: `database/var/astroguard.db`, an absolute location resolved by the
independent database package. Optional `DATABASE_URL` overrides it. Use an absolute URL,
for example `sqlite:///C:/Projects/astroguard-ai/database/var/astroguard.db`. Relative
override URLs follow SQLAlchemy's current-working-directory semantics; use absolute
URLs to avoid accidentally creating different databases from different shells.

The integration deliberately rejects in-memory SQLite and non-SQLite URLs when the
SQLite backend is selected. A missing database package, unsupported configuration,
failed migration or unavailable database never silently falls back to memory.
An unmigrated database returns 503 from /api/v1/ready and storage-backed reads;
/health remains a liveness endpoint and reports the selected adapter. Educational
catalog endpoints remain independent of database readiness.

Migration and seed are explicit commands. Startup, GET requests and browser refresh
never migrate, reseed or evaluate new data. `prepare_database` migrates without seeding
unless --seed is passed. Repeated seeding preserves existing records; the teammate's
seed skips an existing demo mission and does not repair incomplete fixture sets.
Inspect/back up partial databases rather than deleting them or silently overwriting rows.
The independent `astroguard_db.migrate/seed` commands remain available but read the
process environment, not backend/.env; the backend prepare command avoids a URL mismatch.

## Runtime lifecycle and compatibility fixes

- Owned SQLite factories are created at application lifespan entry and disposed on
  shutdown. Restart opens the same file. Owned memory factories close on shutdown
  and reset on restart. Injected adapters remain caller-owned and are not disposed.
- SQLite remains independently installable and never imports backend modules.
- One demonstrated fix in the teammate's repository code: check-in vital values now
  reconstruct in indicator/id order rather than random UUID order. This preserves
  exact multi-vital check-in command replay and canonical assessment inputs.
- Concurrent identical SQLite check-in requests initially reproduced a duplicate
  constraint conflict. Backend command services now reopen/retry repository conflicts
  up to three attempts, allowing a committed receipt to replay. Deliberate public
  workflow errors still return immediately. Persistent constraint conflicts remain
  409; unavailable storage remains 503. No adapter-specific SQL appears in services.
- Memory alert list semantics now match SQLite: state=open includes acknowledged
  unresolved alerts. get_open already had that meaning. No severity, alert-lifecycle
  field or API response shape changed.
- Overview and Mission Simulator display storage-specific persistence text based on
  the existing health response's adapter field. Refresh the browser after cutover
  to reload that root connection state.
- SQLite package dependencies were installed into .venv, and the editable backend
  was refreshed with its sqlite extra. `pip check` reports no broken requirements.

## Preserved data from the running memory app

The old app's active demo run was explicitly stopped before the final export so
automatic ticks could not race the cutover. Its existing telemetry remains stored;
start a new run to continue a demonstration.

API-visible records were exported to Git-ignored local files:

- `database/var/memory-before-sqlite.json`: initial safety export.
- `database/var/memory-cutover-export.json`: final stable cutover export.

The final imported dataset preserves 1 mission, 2 astronauts, 1 simulation run,
14 check-ins, 399 health readings, 258 environmental readings, 130 assessments
and 1 alert, including shared fixture records already present in SQLite.

The explicit importer validates shared DTOs, checks duplicate immutable records,
adds new observations in one transaction, preserves supported lifecycle state,
refuses to rewind newer run progress and verifies reconstructed check-ins before
commit. Any failure rolls back the whole import. Repeating an identical import
does not duplicate observations. It is not an automatic or general-purpose merge
service: use it only for a reviewed, quiescent export at cutover.

```powershell
.\.venv\Scripts\python.exe -m app.import_memory_export database/var/memory-cutover-export.json
```

**Historical memory command receipts were not available through the existing API.**
The old observed records are preserved, but their original runtime retry UUIDs cannot
be replayed as historical commands after transfer. No receipts or missing measurements
were fabricated. Commands created after SQLite cutover persist their receipts normally,
and exact replay survives restart. Shared seeded receipts remain intact.

The SQLite file and safety exports are local development data under database/var/,
ignored by Git. They are not committed or automatically shared with the teammate.
Back up the database while the server is stopped (or use SQLite's backup API); do
not copy only part of an active SQLite journal/WAL set.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest shared/tests backend/tests database/tests -v
.\.venv\Scripts\python.exe -m pip check
cd frontend
npm.cmd test -- --run
npm.cmd run build
```

All original tests remain. New API integration tests use disposable SQLite files and
cover multi-vital replay, concurrent identical commands, full check-in/telemetry/
assessment/alert workflows across new application lifespans, failure rollback at
multiple write boundaries, ownership isolation, unsupported/unmigrated storage,
adapter shutdown ownership, atomic memory-export import and a separate Python
process replaying a committed check-in. Three UI tests cover accurate persistence
messages for SQLite, memory and unknown modes.

The first combined full validation run overloaded the laptop with eight concurrent
jsdom workers, Python tests and a production build, causing UI interaction timeouts.
Vitest now limits concurrency to two workers; all existing assertions and timeouts
remain unchanged. The frontend suite then passed. This is a resource setting, not
test isolation removal or skipped coverage. Production retains the existing nonfatal
Recharts-related large-chunk warning.

Final results: **253 shared/backend/database tests passed** (including all 25 teammate
database tests and 16 SQLite integration cases), **86 frontend tests passed**, production
build passed, and pip check reported no broken requirements. A real live API check
confirmed adapter=sqlite, readiness=true and the imported record totals above. No
manual browser walkthrough is claimed. The main JavaScript bundle remains about
700 kB minified / 208 kB gzipped with a nonfatal size warning.

## Manual persistence demo

1. Open http://127.0.0.1:5173/ and refresh after cutover. Confirm SQLite persistence
   text. http://127.0.0.1:8000/api/v1/health should report adapter=sqlite, and /ready true.
2. Save a fictional daily check-in on an unused UTC date. Note its values and assessment.
3. Start a new fictional simulation on Overview; advance a few ticks and pause. Note
   values, timestamps, run progress and any generated assessment/alert.
4. Acknowledge an open alert if one exists. Refresh the browser; all committed records
   should remain.
5. Stop Uvicorn with Ctrl+C and restart it using the same command and DATABASE_URL.
   Refresh React. Check-in history, telemetry, assessments and alert state must remain.
   Playback intentionally does not resume automatically.
6. Switch astronauts and verify their own records remain separate. Education pages
   should continue functioning without causing writes.

## Limits and maintenance

SQLite is a local, single-writer development store, not a deployed multi-user database.
Busy/unavailable storage can return 503 and should be retried with the same command
key. Prefer one Uvicorn worker for this demo. No WAL tuning, cloud synchronization,
real sensor ingestion or production backup scheduler was added. Existing authored
educational rules remain fictional and have no clinical validation.

## Changed files

- Backend settings, app lifespan and optional SQLite package extra; new runtime adapter
  selector, prepare command and reviewed-export importer.
- Backend check-in/simulation/assessment command conflict retries and memory alert filter.
- Database repository check-in reconstruction ordering (one compatibility fix); database
  README updated. No migration or ORM schema was modified.
- Integration/config tests; pytest default discovery now includes database/tests.
- Storage-aware frontend notices, three UI tests, and Vitest worker limit.
- README, backend/database READMEs, development documentation and this report.
- Ignored local backend/.env, SQLite file and API export backups; database/var ignore rule.

The earlier database-sync-review.md is retained as the historical pre-integration review.
No commits, pushes or migrations outside the configured local development file occurred.
