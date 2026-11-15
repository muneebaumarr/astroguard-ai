# FastAPI backend

Developer A owns API routes, services, memory adapter, simulation and assessments.
Depend on astroguard_contracts; inject repositories through its UnitOfWork.
Phases 0–6 provide /api/v1 profiles, check-ins, deterministic telemetry, educational
assessments/alerts and a read-only education catalog. Runtime repositories use either
the memory adapter or Developer B's independent `astroguard_db` SQLite adapter.
Settings() defaults to memory for explicit tests; backend/.env.example selects SQLite
for normal local setup. Missing/broken SQLite never silently falls back to memory.

Install shared, database, then backend with its sqlite/test extras. Apply migrations
and seed explicitly using `python -m app.prepare_database --seed`; startup and GET
requests do not migrate or seed. See [SQLite integration](../docs/sqlite-integration.md)
for exact PowerShell commands, configuration, cutover limitations and tests.
