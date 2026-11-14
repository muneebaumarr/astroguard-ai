# Database handoff

Developer B owns the independently installable astroguard_db package, SQLite,
SQLAlchemy models, Alembic migrations, repository adapters, seeds and tests.
No database implementation exists in Phase 0. requirements.txt declares the
shared dependency for this boundary, not an installable database package.

Implement every protocol in astroguard_contracts.repositories. Import shared
DTOs and errors; never import backend modules or return ORM objects.
Expose create_uow() and check_ready() through an adapter factory. Transactions
commit only explicitly; exceptions or uncommitted exits roll back. Preserve
atomic check-in/reading/assessment/alert/receipt writes and atomic simulator ticks.

Enable foreign keys, enforce shared uniqueness constraints, use short sessions,
and translate storage failures to shared errors. Supply migration commands,
repeatable seeds consuming shared fixtures, and the common repository acceptance
suite once adapters exist. Do not commit local SQLite files.
