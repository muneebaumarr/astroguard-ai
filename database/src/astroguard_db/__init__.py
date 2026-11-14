"""AstroGuard SQLite persistence adapter.

Backend usage:
    from astroguard_db import SqliteAdapterFactory
    factory = SqliteAdapterFactory()          # uses DATABASE_URL or database/var/astroguard.db
    factory.check_ready()
    with factory.create_uow() as uow:
        uow.astronauts.list(AstronautQuery())
        uow.commit()                          # only when writing
"""
from .factory import SqliteAdapterFactory
from .uow import SqliteUnitOfWork

__all__ = ["SqliteAdapterFactory", "SqliteUnitOfWork"]
