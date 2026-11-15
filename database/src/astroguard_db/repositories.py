"""SQLite implementations of every protocol in astroguard_contracts.repositories.

Rules (docs/development.md):
- Methods never commit; the UnitOfWork commits explicitly.
- Methods return detached shared DTOs, never ORM rows.
- History ascends by observed_at then id. Assessments/alerts descend by
  evaluated_at/opened_at then id. Missions, astronauts and runs ascend by id.
- Time filters include `from` and exclude `to`.
- Uniqueness/foreign-key failures -> Conflict; stale tick -> ConcurrentWrite;
  storage failures -> RepositoryUnavailable.
"""
from __future__ import annotations

import functools
from datetime import date
from enum import Enum

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from astroguard_contracts.dto import (
    Alert, AlertQuery, Assessment, AssessmentQuery, Astronaut, AstronautQuery,
    CheckinQuery, CommandReceipt, DailyCheckin, EnvironmentalReading,
    EnvironmentalReadingQuery, HealthReading, HealthReadingQuery, HealthValue,
    Mission, MissionQuery, Page, SimulationRun, SimulationRunQuery,
)
from astroguard_contracts.enums import (
    AlertState, EnvironmentalIndicator, HealthIndicator, RunStatus, Source,
)
from astroguard_contracts.errors import (
    ConcurrentWrite, Conflict, RepositoryError, RepositoryUnavailable,
)

from .models import (
    AlertRow, AssessmentRow, AstronautRow, CheckinRow, CommandReceiptRow,
    EnvironmentalReadingRow, HealthReadingRow, MissionRow, SimulationRunRow,
)

ACTIVE_ALERT_STATES = (AlertState.OPEN.value, AlertState.ACKNOWLEDGED.value)
ACTIVE_RUN_STATES = (RunStatus.PAUSED.value, RunStatus.RUNNING.value)
TERMINAL_RUN_STATES = (RunStatus.STOPPED.value, RunStatus.FAILED.value)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _v(value):
    """Enum -> stored string value."""
    return value.value if isinstance(value, Enum) else value


def translate_errors(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except RepositoryError:
            raise
        except IntegrityError as exc:
            raise Conflict(f"Constraint violation: {exc.orig}") from exc
        except OperationalError as exc:
            raise RepositoryUnavailable(f"Database unavailable: {exc.orig}") from exc
    return wrapper


def _time_filters(column, query) -> list:
    filters = []
    if query.from_at is not None:
        filters.append(column >= query.from_at)
    if query.to is not None:
        filters.append(column < query.to)
    return filters


def _paged(session: Session, row_cls, filters, order_by, query, to_dto, dto_cls):
    count_stmt = select(func.count()).select_from(row_cls)
    rows_stmt = select(row_cls)
    if filters:
        count_stmt = count_stmt.where(*filters)
        rows_stmt = rows_stmt.where(*filters)
    total = session.scalar(count_stmt) or 0
    rows = session.scalars(rows_stmt.order_by(*order_by).limit(query.limit).offset(query.offset)).all()
    return Page[dto_cls](items=[to_dto(r) for r in rows], total=total, limit=query.limit, offset=query.offset)


# ---------------------------------------------------------------------------
# Row -> DTO
# ---------------------------------------------------------------------------
def mission_dto(r: MissionRow) -> Mission:
    return Mission(id=r.id, created_at=r.created_at, name=r.name, environment=r.environment,
                   started_at=r.started_at, ended_at=r.ended_at, description=r.description)


def astronaut_dto(r: AstronautRow) -> Astronaut:
    return Astronaut(id=r.id, created_at=r.created_at, mission_id=r.mission_id,
                     display_name=r.display_name, role=r.role)


def health_dto(r: HealthReadingRow) -> HealthReading:
    return HealthReading(id=r.id, created_at=r.created_at, astronaut_id=r.astronaut_id,
                         indicator=r.indicator, value=r.value, unit=r.unit,
                         observed_at=r.observed_at, source=r.source, context=r.context,
                         checkin_id=r.checkin_id, simulation_run_id=r.simulation_run_id,
                         tick_index=r.tick_index)


def environmental_dto(r: EnvironmentalReadingRow) -> EnvironmentalReading:
    return EnvironmentalReading(id=r.id, created_at=r.created_at, mission_id=r.mission_id,
                                indicator=r.indicator, value=r.value, unit=r.unit,
                                observed_at=r.observed_at, source=r.source,
                                simulation_run_id=r.simulation_run_id, tick_index=r.tick_index)


def assessment_dto(r: AssessmentRow) -> Assessment:
    return Assessment(id=r.id, created_at=r.created_at, astronaut_id=r.astronaut_id,
                      evaluated_at=r.evaluated_at, status=r.status,
                      ruleset_version=r.ruleset_version, input_fingerprint=r.input_fingerprint,
                      coverage=r.coverage, results=r.results)


def alert_dto(r: AlertRow) -> Alert:
    return Alert(id=r.id, created_at=r.created_at, astronaut_id=r.astronaut_id, rule_id=r.rule_id,
                 workflow_status=r.workflow_status, state=r.state,
                 first_assessment_id=r.first_assessment_id,
                 latest_assessment_id=r.latest_assessment_id, opened_at=r.opened_at,
                 acknowledged_at=r.acknowledged_at, resolved_at=r.resolved_at)


def run_dto(r: SimulationRunRow) -> SimulationRun:
    return SimulationRun(id=r.id, created_at=r.created_at, astronaut_id=r.astronaut_id,
                         mission_id=r.mission_id, scenario=r.scenario, seed=r.seed,
                         simulation_start_at=r.simulation_start_at,
                         interval_seconds=r.interval_seconds, step_seconds=r.step_seconds,
                         scenario_version=r.scenario_version, status=r.status,
                         started_at=r.started_at, last_tick_index=r.last_tick_index,
                         last_error=r.last_error)


def receipt_dto(r: CommandReceiptRow) -> CommandReceipt:
    return CommandReceipt(id=r.id, created_at=r.created_at, operation=r.operation,
                          request_hash=r.request_hash, result_type=r.result_type,
                          result_id=r.result_id)


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------
class _Repository:
    def __init__(self, session: Session):
        self._s = session


class SqliteMissionRepository(_Repository):
    @translate_errors
    def get(self, id: str) -> Mission | None:
        row = self._s.get(MissionRow, id)
        return mission_dto(row) if row else None

    @translate_errors
    def list(self, query: MissionQuery) -> Page[Mission]:
        return _paged(self._s, MissionRow, [], [MissionRow.id.asc()], query, mission_dto, Mission)

    @translate_errors
    def add(self, record: Mission) -> Mission:
        self._s.add(MissionRow(
            id=record.id, created_at=record.created_at, name=record.name,
            environment=_v(record.environment), started_at=record.started_at,
            ended_at=record.ended_at, description=record.description, is_demo=True,
        ))
        self._s.flush()
        return record


class SqliteAstronautRepository(_Repository):
    @translate_errors
    def get(self, id: str) -> Astronaut | None:
        row = self._s.get(AstronautRow, id)
        return astronaut_dto(row) if row else None

    @translate_errors
    def list(self, query: AstronautQuery) -> Page[Astronaut]:
        filters = [AstronautRow.mission_id == query.mission_id] if query.mission_id else []
        return _paged(self._s, AstronautRow, filters, [AstronautRow.id.asc()], query, astronaut_dto, Astronaut)

    @translate_errors
    def add(self, record: Astronaut) -> Astronaut:
        self._s.add(AstronautRow(
            id=record.id, created_at=record.created_at, mission_id=record.mission_id,
            display_name=record.display_name, role=record.role, is_demo=True,
        ))
        self._s.flush()
        return record


class SqliteCheckinRepository(_Repository):
    """Check-in rows hold self-reported fields only. Vital values are stored once,
    in health_readings linked by checkin_id, and rebuilt into DailyCheckin.readings.
    The service adds those HealthReadings in the same UnitOfWork."""

    def _dto(self, row: CheckinRow) -> DailyCheckin:
        vitals = self._s.scalars(
            select(HealthReadingRow)
            .where(HealthReadingRow.checkin_id == row.id)
            .order_by(HealthReadingRow.indicator.asc(), HealthReadingRow.id.asc())
        ).all()
        return DailyCheckin(
            id=row.id, created_at=row.created_at, astronaut_id=row.astronaut_id,
            checkin_date=row.checkin_date, observed_at=row.observed_at, context=row.context,
            readings=[HealthValue(indicator=v.indicator, value=v.value, unit=v.unit) for v in vitals],
            sleep_hours=row.sleep_hours, mood=row.mood, stress=row.stress,
            symptoms=list(row.symptoms or []), exercise_minutes=row.exercise_minutes,
            notes=row.notes,
        )

    @translate_errors
    def get(self, id: str) -> DailyCheckin | None:
        row = self._s.get(CheckinRow, id)
        return self._dto(row) if row else None

    @translate_errors
    def get_for_date(self, astronaut_id: str, date: date) -> DailyCheckin | None:
        row = self._s.scalars(
            select(CheckinRow).where(CheckinRow.astronaut_id == astronaut_id, CheckinRow.checkin_date == date)
        ).first()
        return self._dto(row) if row else None

    @translate_errors
    def list(self, astronaut_id: str, query: CheckinQuery) -> Page[DailyCheckin]:
        filters = [CheckinRow.astronaut_id == astronaut_id, *_time_filters(CheckinRow.observed_at, query)]
        return _paged(self._s, CheckinRow, filters, [CheckinRow.observed_at.asc(), CheckinRow.id.asc()],
                      query, self._dto, DailyCheckin)

    @translate_errors
    def add(self, record: DailyCheckin) -> DailyCheckin:
        self._s.add(CheckinRow(
            id=record.id, created_at=record.created_at, astronaut_id=record.astronaut_id,
            checkin_date=record.checkin_date, observed_at=record.observed_at,
            context=_v(record.context), sleep_hours=record.sleep_hours, mood=record.mood,
            stress=record.stress, symptoms=list(record.symptoms),
            exercise_minutes=record.exercise_minutes, notes=record.notes, is_demo=True,
        ))
        self._s.flush()
        return record


class SqliteHealthReadingRepository(_Repository):
    def _check_ownership(self, record: HealthReading) -> None:
        if record.checkin_id is not None:
            owner = self._s.scalar(select(CheckinRow.astronaut_id).where(CheckinRow.id == record.checkin_id))
            if owner != record.astronaut_id:
                raise Conflict("Reading astronaut does not match its check-in")
        if record.simulation_run_id is not None:
            owner = self._s.scalar(
                select(SimulationRunRow.astronaut_id).where(SimulationRunRow.id == record.simulation_run_id))
            if owner != record.astronaut_id:
                raise Conflict("Reading astronaut does not match its simulation run")

    @translate_errors
    def add_many(self, records: list[HealthReading]) -> list[HealthReading]:
        for record in records:
            self._check_ownership(record)
        self._s.add_all([
            HealthReadingRow(
                id=r.id, created_at=r.created_at, astronaut_id=r.astronaut_id,
                indicator=_v(r.indicator), value=r.value, unit=_v(r.unit),
                observed_at=r.observed_at, source=_v(r.source), context=_v(r.context),
                checkin_id=r.checkin_id, simulation_run_id=r.simulation_run_id,
                tick_index=r.tick_index, is_demo=True,
            )
            for r in records
        ])
        self._s.flush()
        return list(records)

    @translate_errors
    def list(self, astronaut_id: str, query: HealthReadingQuery) -> Page[HealthReading]:
        filters = [HealthReadingRow.astronaut_id == astronaut_id,
                   *_time_filters(HealthReadingRow.observed_at, query)]
        if query.indicator is not None:
            filters.append(HealthReadingRow.indicator == _v(query.indicator))
        if query.source is not None:
            filters.append(HealthReadingRow.source == _v(query.source))
        if query.simulation_run_id is not None:
            filters.append(HealthReadingRow.simulation_run_id == query.simulation_run_id)
        return _paged(self._s, HealthReadingRow, filters,
                      [HealthReadingRow.observed_at.asc(), HealthReadingRow.id.asc()],
                      query, health_dto, HealthReading)

    @translate_errors
    def latest_by_indicator(self, astronaut_id: str, source: Source | None = None) -> dict[HealthIndicator, HealthReading]:
        latest: dict[HealthIndicator, HealthReading] = {}
        for indicator in HealthIndicator:
            stmt = select(HealthReadingRow).where(
                HealthReadingRow.astronaut_id == astronaut_id,
                HealthReadingRow.indicator == indicator.value,
            )
            if source is not None:
                stmt = stmt.where(HealthReadingRow.source == _v(source))
            row = self._s.scalars(
                stmt.order_by(HealthReadingRow.observed_at.desc(), HealthReadingRow.id.desc()).limit(1)
            ).first()
            if row is not None:
                latest[indicator] = health_dto(row)
        return latest


class SqliteEnvironmentalReadingRepository(_Repository):
    @translate_errors
    def add_many(self, records: list[EnvironmentalReading]) -> list[EnvironmentalReading]:
        for r in records:
            run_mission = self._s.scalar(
                select(SimulationRunRow.mission_id).where(SimulationRunRow.id == r.simulation_run_id))
            if run_mission != r.mission_id:
                raise Conflict("Environmental reading mission does not match its simulation run")
        self._s.add_all([
            EnvironmentalReadingRow(
                id=r.id, created_at=r.created_at, mission_id=r.mission_id,
                indicator=_v(r.indicator), value=r.value, unit=_v(r.unit),
                observed_at=r.observed_at, source=_v(r.source),
                simulation_run_id=r.simulation_run_id, tick_index=r.tick_index, is_demo=True,
            )
            for r in records
        ])
        self._s.flush()
        return list(records)

    @translate_errors
    def list(self, mission_id: str, query: EnvironmentalReadingQuery) -> Page[EnvironmentalReading]:
        filters = [EnvironmentalReadingRow.mission_id == mission_id,
                   *_time_filters(EnvironmentalReadingRow.observed_at, query)]
        if query.indicator is not None:
            filters.append(EnvironmentalReadingRow.indicator == _v(query.indicator))
        if query.source is not None:
            filters.append(EnvironmentalReadingRow.source == _v(query.source))
        if query.simulation_run_id is not None:
            filters.append(EnvironmentalReadingRow.simulation_run_id == query.simulation_run_id)
        return _paged(self._s, EnvironmentalReadingRow, filters,
                      [EnvironmentalReadingRow.observed_at.asc(), EnvironmentalReadingRow.id.asc()],
                      query, environmental_dto, EnvironmentalReading)

    @translate_errors
    def latest_by_indicator(self, mission_id: str) -> dict[EnvironmentalIndicator, EnvironmentalReading]:
        latest: dict[EnvironmentalIndicator, EnvironmentalReading] = {}
        for indicator in EnvironmentalIndicator:
            row = self._s.scalars(
                select(EnvironmentalReadingRow)
                .where(EnvironmentalReadingRow.mission_id == mission_id,
                       EnvironmentalReadingRow.indicator == indicator.value)
                .order_by(EnvironmentalReadingRow.observed_at.desc(), EnvironmentalReadingRow.id.desc())
                .limit(1)
            ).first()
            if row is not None:
                latest[indicator] = environmental_dto(row)
        return latest


class SqliteAssessmentRepository(_Repository):
    @translate_errors
    def get(self, id: str) -> Assessment | None:
        row = self._s.get(AssessmentRow, id)
        return assessment_dto(row) if row else None

    @translate_errors
    def get_by_fingerprint(self, astronaut_id: str, ruleset_version: str, fingerprint: str) -> Assessment | None:
        row = self._s.scalars(select(AssessmentRow).where(
            AssessmentRow.astronaut_id == astronaut_id,
            AssessmentRow.ruleset_version == ruleset_version,
            AssessmentRow.input_fingerprint == fingerprint,
        )).first()
        return assessment_dto(row) if row else None

    @translate_errors
    def list(self, astronaut_id: str, query: AssessmentQuery) -> Page[Assessment]:
        filters = [AssessmentRow.astronaut_id == astronaut_id,
                   *_time_filters(AssessmentRow.evaluated_at, query)]
        return _paged(self._s, AssessmentRow, filters,
                      [AssessmentRow.evaluated_at.desc(), AssessmentRow.id.desc()],
                      query, assessment_dto, Assessment)

    @translate_errors
    def add(self, record: Assessment) -> Assessment:
        self._s.add(AssessmentRow(
            id=record.id, created_at=record.created_at, astronaut_id=record.astronaut_id,
            evaluated_at=record.evaluated_at, status=_v(record.status),
            ruleset_version=record.ruleset_version, input_fingerprint=record.input_fingerprint,
            coverage=record.coverage.model_dump(mode="json"),
            results=[result.model_dump(mode="json") for result in record.results],
        ))
        self._s.flush()
        return record


class SqliteAlertRepository(_Repository):
    """A state=open filter also returns acknowledged alerts: acknowledged but
    unresolved alerts count as open (docs/development.md)."""

    @translate_errors
    def get(self, id: str) -> Alert | None:
        row = self._s.get(AlertRow, id)
        return alert_dto(row) if row else None

    @translate_errors
    def list(self, astronaut_id: str, query: AlertQuery) -> Page[Alert]:
        filters = [AlertRow.astronaut_id == astronaut_id]
        if query.state == AlertState.OPEN:
            filters.append(AlertRow.state.in_(ACTIVE_ALERT_STATES))
        elif query.state is not None:
            filters.append(AlertRow.state == _v(query.state))
        return _paged(self._s, AlertRow, filters, [AlertRow.opened_at.desc(), AlertRow.id.desc()],
                      query, alert_dto, Alert)

    @translate_errors
    def get_open(self, astronaut_id: str, rule_id: str) -> Alert | None:
        row = self._s.scalars(select(AlertRow).where(
            AlertRow.astronaut_id == astronaut_id,
            AlertRow.rule_id == rule_id,
            AlertRow.state.in_(ACTIVE_ALERT_STATES),
        )).first()
        return alert_dto(row) if row else None

    @translate_errors
    def add(self, record: Alert) -> Alert:
        self._s.add(AlertRow(
            id=record.id, created_at=record.created_at, astronaut_id=record.astronaut_id,
            rule_id=record.rule_id, workflow_status=_v(record.workflow_status),
            state=_v(record.state), first_assessment_id=record.first_assessment_id,
            latest_assessment_id=record.latest_assessment_id, opened_at=record.opened_at,
            acknowledged_at=record.acknowledged_at, resolved_at=record.resolved_at,
        ))
        self._s.flush()
        return record

    @translate_errors
    def update(self, record: Alert) -> Alert:
        row = self._s.get(AlertRow, record.id)
        if row is None:
            raise Conflict("Alert does not exist")
        unchanged = (
            row.astronaut_id == record.astronaut_id and row.rule_id == record.rule_id
            and row.first_assessment_id == record.first_assessment_id
            and row.opened_at == record.opened_at and row.created_at == record.created_at
        )
        if not unchanged:
            raise Conflict("Alert identity fields cannot change")
        row.workflow_status = _v(record.workflow_status)
        row.state = _v(record.state)
        row.latest_assessment_id = record.latest_assessment_id
        row.acknowledged_at = record.acknowledged_at
        row.resolved_at = record.resolved_at
        self._s.flush()
        return record


class SqliteSimulationRunRepository(_Repository):
    @staticmethod
    def _slot(status) -> int | None:
        return 1 if _v(status) in ACTIVE_RUN_STATES else None

    @translate_errors
    def get(self, id: str) -> SimulationRun | None:
        row = self._s.get(SimulationRunRow, id)
        return run_dto(row) if row else None

    @translate_errors
    def get_active(self) -> SimulationRun | None:
        row = self._s.scalars(
            select(SimulationRunRow).where(SimulationRunRow.status.in_(ACTIVE_RUN_STATES))
        ).first()
        return run_dto(row) if row else None

    @translate_errors
    def list(self, query: SimulationRunQuery) -> Page[SimulationRun]:
        filters = [SimulationRunRow.status == _v(query.status)] if query.status is not None else []
        return _paged(self._s, SimulationRunRow, filters, [SimulationRunRow.id.asc()],
                      query, run_dto, SimulationRun)

    @translate_errors
    def add(self, record: SimulationRun) -> SimulationRun:
        astronaut_mission = self._s.scalar(
            select(AstronautRow.mission_id).where(AstronautRow.id == record.astronaut_id))
        if astronaut_mission != record.mission_id:
            raise Conflict("Simulation run mission must match the astronaut's mission")
        self._s.add(SimulationRunRow(
            id=record.id, created_at=record.created_at, astronaut_id=record.astronaut_id,
            mission_id=record.mission_id, scenario=_v(record.scenario), seed=record.seed,
            simulation_start_at=record.simulation_start_at,
            interval_seconds=record.interval_seconds, step_seconds=record.step_seconds,
            scenario_version=record.scenario_version, status=_v(record.status),
            started_at=record.started_at, last_tick_index=record.last_tick_index,
            last_error=record.last_error, active_slot=self._slot(record.status),
        ))
        self._s.flush()
        return record

    @translate_errors
    def update(self, record: SimulationRun, expected_last_tick: int) -> SimulationRun:
        current = self._s.get(SimulationRunRow, record.id)
        if current is None:
            raise Conflict("Simulation run does not exist")
        self._s.refresh(current)
        if current.status in TERMINAL_RUN_STATES and _v(record.status) != current.status:
            raise Conflict("Stopped or failed runs cannot change state")
        unchanged = (
            current.astronaut_id == record.astronaut_id and current.mission_id == record.mission_id
            and current.scenario == _v(record.scenario) and current.seed == record.seed
            and current.scenario_version == record.scenario_version
            and current.simulation_start_at == record.simulation_start_at
            and current.interval_seconds == record.interval_seconds
            and current.step_seconds == record.step_seconds
        )
        if not unchanged:
            raise Conflict("Simulation run identity fields cannot change")
        result = self._s.execute(
            update(SimulationRunRow)
            .where(SimulationRunRow.id == record.id,
                   SimulationRunRow.last_tick_index == expected_last_tick)
            .values(status=_v(record.status), started_at=record.started_at,
                    last_tick_index=record.last_tick_index, last_error=record.last_error,
                    active_slot=self._slot(record.status))
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise ConcurrentWrite("Simulation run progress changed; expected_last_tick is stale")
        self._s.expire(current)
        return record


class SqliteCommandReceiptRepository(_Repository):
    @translate_errors
    def get(self, command_id: str) -> CommandReceipt | None:
        row = self._s.get(CommandReceiptRow, command_id)
        return receipt_dto(row) if row else None

    @translate_errors
    def add(self, record: CommandReceipt) -> CommandReceipt:
        self._s.add(CommandReceiptRow(
            id=record.id, created_at=record.created_at, operation=record.operation,
            request_hash=record.request_hash, result_type=record.result_type,
            result_id=record.result_id,
        ))
        self._s.flush()
        return record
