# Installation and ownership

Phase 0 contract installation is documented below. The running Phase 1 application,
its configuration and startup commands are documented in [phase1-development.md](phase1-development.md).

Use Python 3.13 on both laptops. From repository root in PowerShell:

```powershell
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install -e './shared[test]' -c shared/constraints-py313.txt
.\.venv313\Scripts\python.exe -m pytest shared/tests
.\.venv313\Scripts\python.exe -c "from astroguard_contracts.fixtures import representative_fixtures; print({k: len(v) for k, v in representative_fixtures().items()})"
```

If the launcher does not detect an installed 3.13, use its full python.exe path
for the first command. Do not replace a working environment without checking its
contents. No activation or PowerShell execution-policy change is necessary.

The shared package is independently editable-installable. In a runtime environment,
install `-e ./shared` before consuming backend/database requirements. Both requirement
files name the same installed shared distribution. Phase 1 additionally supplies an
installable backend and its runtime dependencies. Developer B's independent database
package is now supplied and integrated through the shared adapter boundary. Install
`-e ./database` and the backend sqlite extra for persistent runtime storage. See
[SQLite setup and persistence verification](sqlite-integration.md) for current commands.

## Ownership and Git workflow

| Owner | Directory / responsibility | Branch |
|---|---|---|
| A | frontend, backend, memory adapter, simulator, assessments, integration | feature/app |
| B | database, ORM, migrations, repositories, persistence tests | feature/database |
| A coordinates; both review | shared contracts, fixtures, root docs/config | agreed contract PR |

Merge a shared-contract commit to main before both feature branches diverge.
Use small reviewed PRs and update branches from main at each integration checkpoint.
Do not commit SQLite files, environments, credentials or generated artifacts.
Change shared interfaces only through a coordinated contract PR with examples and tests.
Never rewrite a migration already merged into main.

## Database teammate acceptance obligations

Implement all protocols in shared/src/astroguard_contracts/repositories.py, explicit
commit/rollback, atomic multi-repository writes, deterministic ordering and pagination,
unique constraints, detached DTO reconstruction and shared error translation.
Supply readiness checks, fresh-database Alembic migrations, idempotent seed commands
using the fixture definitions, and temporary-file SQLite tests. Implement an adapter
parity suite together with A's memory adapter. Phase 0 tests validate contracts only;
they do not claim to test unimplemented adapter behavior.

Latest methods return one value per indicator, ordered by observed_at then id when
selecting ties. History is ascending observed_at/id; assessments and alerts descend
by evaluation/opening time then id. Missions, astronauts and runs use ascending id.
Date filters include from and exclude to; check-ins filter observed_at. Assessment
filters use evaluated_at. Alerts acknowledged but unresolved count as open.

UnitOfWork.__exit__ must not suppress errors. Roll back an exception or uncommitted
exit and release resources. Repository methods never commit independently. Duplicate
keys become Conflict; stale expected_last_tick becomes ConcurrentWrite; unavailable
storage becomes RepositoryUnavailable. No silent fallback to memory.
