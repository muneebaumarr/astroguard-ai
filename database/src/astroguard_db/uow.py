"""SQLite UnitOfWork. Commits only when commit() is called; anything else rolls back."""
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from astroguard_contracts.errors import Conflict, RepositoryUnavailable

from .repositories import (
    SqliteAlertRepository, SqliteAssessmentRepository, SqliteAstronautRepository,
    SqliteCheckinRepository, SqliteCommandReceiptRepository,
    SqliteEnvironmentalReadingRepository, SqliteHealthReadingRepository,
    SqliteMissionRepository, SqliteSimulationRunRepository,
)


class SqliteUnitOfWork:
    """Use as: with factory.create_uow() as uow: ...; uow.commit()"""

    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory
        self._session: Session | None = None

    def __enter__(self) -> "SqliteUnitOfWork":
        session = self._session_factory()
        self._session = session
        self.missions = SqliteMissionRepository(session)
        self.astronauts = SqliteAstronautRepository(session)
        self.checkins = SqliteCheckinRepository(session)
        self.health_readings = SqliteHealthReadingRepository(session)
        self.environmental_readings = SqliteEnvironmentalReadingRepository(session)
        self.assessments = SqliteAssessmentRepository(session)
        self.alerts = SqliteAlertRepository(session)
        self.simulation_runs = SqliteSimulationRunRepository(session)
        self.command_receipts = SqliteCommandReceiptRepository(session)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        # Roll back anything not committed (after an exception or a missing commit),
        # release the connection, and never suppress the original error.
        if self._session is None:
            return None
        try:
            self._session.rollback()
        finally:
            self._session.close()
            self._session = None
        return None

    def _require_session(self) -> Session:
        if self._session is None:
            raise RuntimeError("Use the unit of work inside a 'with' block")
        return self._session

    def commit(self) -> None:
        session = self._require_session()
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise Conflict(f"Constraint violation: {exc.orig}") from exc
        except OperationalError as exc:
            session.rollback()
            raise RepositoryUnavailable(f"Database unavailable: {exc.orig}") from exc

    def rollback(self) -> None:
        self._require_session().rollback()
