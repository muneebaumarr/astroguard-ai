"""SQLite AdapterFactory: what the backend uses to get units of work."""
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from astroguard_contracts.dto import ReadinessResult

from .config import database_url as default_database_url
from .models import REQUIRED_TABLES
from .session import make_engine
from .uow import SqliteUnitOfWork

ADAPTER_NAME = "sqlite"


class SqliteAdapterFactory:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or default_database_url()
        self._engine = make_engine(self.database_url)
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)

    def create_uow(self) -> SqliteUnitOfWork:
        return SqliteUnitOfWork(self._session_factory)

    def check_ready(self) -> ReadinessResult:
        try:
            with self._engine.connect() as connection:
                tables = set(inspect(connection).get_table_names())
        except SQLAlchemyError as exc:
            return ReadinessResult(ready=False, adapter=ADAPTER_NAME,
                                   detail=f"Database unavailable ({exc.__class__.__name__})")
        missing = sorted(REQUIRED_TABLES - tables)
        if missing:
            return ReadinessResult(
                ready=False, adapter=ADAPTER_NAME,
                detail="Database is not migrated. Run: alembic -c database/alembic.ini upgrade head "
                       f"(missing tables: {', '.join(missing)})",
            )
        return ReadinessResult(ready=True, adapter=ADAPTER_NAME)

    def dispose(self) -> None:
        """Close pooled connections (useful in tests and on shutdown)."""
        self._engine.dispose()
