# Database handoff: synced for review, not integrated

Historical pre-integration review. The user subsequently approved integration;
see [completed SQLite integration](sqlite-integration.md) for the current state.

## Sync result

Fetched `origin` from https://github.com/muneebaumarr/astroguard-ai.
The requested source is `origin/main/database`.

- Main commit: `caebe9c923c76c42352983fc5eecdd8c4925ad2a`.
- Local `feature/app` HEAD already points to that same commit.
- Friend's remote branch: `origin/khadeeja_database`, commit
  `d7b35bd42d647340cbd6f88730679916b3b7dd50`.
- Local, main and the friend's branch contain identical database directories.
- All 19 tracked database files are already present locally. No overwrite, merge,
  checkout or duplicate copy was necessary. Fetch discovered the friend's branch.
- No database code was changed, dependencies installed, migrations run, seed command
  executed, or live application storage switched. No commit or push was performed.

## What is available to review

The independent Python 3.13 package is in `database/src/astroguard_db`:

- `models.py`: SQLAlchemy models for the nine shared contract tables.
- `repositories.py`: SQLite implementations of the shared repository interfaces.
- `uow.py`: explicit transactions and rollback/connection cleanup.
- `factory.py`: `SqliteAdapterFactory`, `create_uow()`, `check_ready()`, `dispose()`.
- `session.py`, `config.py`: engine setup, foreign keys and DATABASE_URL location.
- `migrate.py`, `migrations/`, `alembic.ini`: Alembic migration tooling and initial schema.
- `seed.py`: shared fictional fixture loading in one transaction; skips when the demo
  mission already exists.
- `pyproject.toml`, `requirements.txt`: independently installable package/dependencies.
- `tests/`: repository, transaction, migration, readiness and package-boundary tests.

There is no tracked populated SQLite database in the current directory. The supplied
data is reproducible fictional seed definitions from `astroguard_contracts.fixtures`;
the seed command creates records when approved and run later. A teammate's untracked
local database contents are not transferred by Git. Historical deleted .db files were
not restored.

## Initial integration findings (source inspection only)

1. FastAPI currently constructs `MemoryAdapterFactory` and rejects non-memory backend
   configuration. Merely fetching these files does not enable persistent storage.
2. The database factory exposes `dispose()` while memory uses `close()`; application
   ownership and shutdown must handle the selected adapter correctly.
3. `database/README.md` still describes the Phase 0 placeholder and says no database
   implementation exists. It should be updated during the approved handoff integration.
4. Alert filter semantics differ: SQLite's `list(state=open)` includes acknowledged
   unresolved alerts, while the current memory adapter filters the exact state. The
   shared `get_open` method intentionally includes acknowledged records. This list
   filter difference needs a documented parity decision before enabling SQLite.
5. Seed currently treats the existence of the demo mission as proof of completed
   seeding. It will not repair a manually created partial fixture set; determine an
   explicit fresh/existing database policy during integration.
6. Existing database tests are supplied, but were not executed in this sync-only step.
   No installed-package or runtime compatibility claim is made yet. In particular,
   Phase 5 alert/assessment replay and Phase 3 tick transactions need adapter-parity
   and restart-persistence verification against the real FastAPI services.

## Proposed next step, awaiting user approval

After review, install the independent database package in the project environment,
run its tests against disposable temporary databases, verify parity with shared
contracts and current memory behavior, and resolve demonstrated compatibility issues.
Then wire explicit memory/sqlite configuration and correct adapter lifespan, document
migration/seed commands, and test check-ins, telemetry, assessment/alert lifecycle,
idempotency, rollback and persistence across backend restarts. Preserve `/api/v1`
schemas and avoid silently falling back to memory.

No implementation or integration work has begun in this handoff step.
