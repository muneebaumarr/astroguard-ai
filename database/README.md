# AstroGuard SQLite persistence

Developer B's independently installable `astroguard_db` package supplies SQLAlchemy
models, Alembic migrations, nine repositories, explicit UnitOfWork transactions,
readiness, fictional seeding and persistence tests. It imports shared contracts,
never backend/FastAPI modules. Shared contracts have no ORM models.

From the repository root, using Python 3.13:

```powershell
.\.venv\Scripts\python.exe -m pip install -e './shared[test]' -e './database[test]' -e './backend[sqlite,test]'
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
.\.venv\Scripts\python.exe -m app.prepare_database --seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Copy the example only on first setup; preserve existing local configuration. SQLite
defaults to `database/var/astroguard.db`, resolved independently of the shell's current
directory. DATABASE_URL overrides it; prefer an absolute SQLite URL. Both this folder
and backend/.env are ignored by Git. Committed SQLite records survive server restarts.

The independent package also supports `python -m astroguard_db.migrate` and
`python -m astroguard_db.seed`; those commands read DATABASE_URL from the process
environment rather than backend/.env. The backend prepare command uses the exact
same settings as FastAPI and avoids configuring different files accidentally.

Application startup never migrates or seeds. Missing schema makes /api/v1/ready
return 503; no memory fallback occurs. Seed is explicit, atomic and repeatable, but
skips an existing demo mission and does not repair partial fixture sets. Never replace
or delete an existing database to fix a migration without reviewing it first.

Repositories return detached DTOs and never commit independently. History ascends by
observed_at/id; assessments and alerts descend by evaluation/opening time/id. The open
alert list includes acknowledged unresolved records, as does get_open. Both adapters
now agree on that behavior. Check-in readings reconstruct in canonical indicator order
to preserve API idempotency and input fingerprints. The initial migration is unchanged.

Tests: `python -m pytest shared/tests backend/tests database/tests -v` uses temporary
files for database and API integration tests; it does not touch the local development DB.
See [integration report](../docs/sqlite-integration.md) for migration/cutover details,
the exact compatibility fixes, historical retry-key limitation and demo procedure.
