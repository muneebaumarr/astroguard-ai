"""Process-local snapshots with explicit transactions and optimistic commit checks.

Only adapter operations are implemented here, not check-in/simulator business flows.
All nine shared repository protocols are supported for later application services.
"""
from copy import deepcopy
from datetime import date
from threading import RLock
from types import TracebackType
from typing import Generic, TypeVar

from astroguard_contracts import dto as d
from astroguard_contracts.enums import AlertState, EnvironmentalIndicator, HealthIndicator, RunStatus, Source
from astroguard_contracts.errors import ConcurrentWrite, Conflict, RepositoryUnavailable
from astroguard_contracts.fixtures import representative_fixtures
from astroguard_contracts.repositories import UnitOfWork

T = TypeVar("T", bound=d.Record)


def validate_state(state):
    """Cross-record persistence constraints, checked atomically before commit."""
    def require(condition, message):
        if not condition:
            raise Conflict(message)

    def unique(records, key, message):
        keys = [key(record) for record in records]
        require(len(keys) == len(set(keys)), message)

    missions, astronauts = state["missions"], state["astronauts"]
    checkins, runs, assessments = state["checkins"], state["simulation_runs"], state["assessments"]
    for astronaut in astronauts.values():
        require(astronaut.mission_id in missions, "Astronaut mission missing")
    for record in checkins.values():
        require(record.astronaut_id in astronauts, "Check-in astronaut missing")
        linked = [r for r in state["health_readings"].values() if r.checkin_id == record.id]
        actual = {r.indicator: (r.value, r.unit) for r in linked}
        expected = {r.indicator: (r.value, r.unit) for r in record.readings}
        require(actual == expected and len(linked) == len(actual), "Check-in vital values must match linked readings")
    unique(checkins.values(), lambda r: (r.astronaut_id, r.checkin_date), "Duplicate daily check-in")
    for run in runs.values():
        require(run.astronaut_id in astronauts, "Run astronaut missing")
        require(astronauts[run.astronaut_id].mission_id == run.mission_id, "Run mission mismatch")
    active = [r for r in runs.values() if r.status in (RunStatus.PAUSED, RunStatus.RUNNING)]
    require(len(active) <= 1, "Only one active simulation run allowed")
    for reading in state["health_readings"].values():
        require(reading.astronaut_id in astronauts, "Reading astronaut missing")
        if reading.checkin_id:
            require(reading.checkin_id in checkins, "Reading check-in missing")
            checkin = checkins[reading.checkin_id]
            require(checkin.astronaut_id == reading.astronaut_id, "Reading check-in ownership mismatch")
            require(checkin.observed_at == reading.observed_at, "Reading check-in observation mismatch")
        if reading.simulation_run_id:
            require(reading.simulation_run_id in runs, "Reading run missing")
            require(runs[reading.simulation_run_id].astronaut_id == reading.astronaut_id, "Reading run ownership mismatch")
    for reading in state["environmental_readings"].values():
        require(reading.mission_id in missions, "Environment mission missing")
        require(reading.simulation_run_id in runs, "Environment run missing")
        require(runs[reading.simulation_run_id].mission_id == reading.mission_id, "Environment run mission mismatch")
    for key in ("health_readings", "environmental_readings"):
        unique([r for r in state[key].values() if r.simulation_run_id],
               lambda r: (r.simulation_run_id, r.tick_index, r.indicator), "Duplicate simulated tick indicator")
    for assessment in assessments.values():
        require(assessment.astronaut_id in astronauts, "Assessment astronaut missing")
    unique(assessments.values(), lambda r: (r.astronaut_id, r.ruleset_version, r.input_fingerprint), "Duplicate assessment input")
    for alert in state["alerts"].values():
        require(alert.astronaut_id in astronauts, "Alert astronaut missing")
        for assessment_id in (alert.first_assessment_id, alert.latest_assessment_id):
            require(assessment_id in assessments, "Alert assessment missing")
            require(assessments[assessment_id].astronaut_id == alert.astronaut_id, "Alert assessment ownership mismatch")
    unique([r for r in state["alerts"].values() if r.state != AlertState.RESOLVED],
           lambda r: (r.astronaut_id, r.rule_id), "Duplicate active alert")


class MemoryAdapterFactory:
    def __init__(self, fixtures=None):
        source = representative_fixtures() if fixtures is None else fixtures
        names = ("missions", "astronauts", "checkins", "health_readings", "environmental_readings",
                 "assessments", "alerts", "simulation_runs", "command_receipts")
        self._state = {name: {r.id: deepcopy(r) for r in source.get(name, [])} for name in names}
        validate_state(self._state)
        self._revision = 0
        self._lock = RLock()
        self._closed = False

    def create_uow(self) -> UnitOfWork:
        return MemoryUnitOfWork(self)

    def check_ready(self) -> d.ReadinessResult:
        return d.ReadinessResult(ready=not self._closed, adapter="memory",
                                 detail="Process-local fictional fixtures; changes reset on restart")

    def close(self) -> None:
        with self._lock:
            self._closed = True


class Records(Generic[T]):
    def __init__(self, uow, name, model):
        self.uow, self.name, self.model = uow, name, model

    def _table(self):
        self.uow._ensure_active()
        return self.uow._state[self.name]

    def _get(self, id):
        return deepcopy(self._table().get(id))

    def _add(self, record):
        value = self.model.model_validate(record.model_dump())
        table = self._table()
        if value.id in table:
            raise Conflict("Record ID already exists")
        table[value.id] = deepcopy(value)
        self.uow._dirty = True
        return deepcopy(value)

    def _update(self, record):
        value = self.model.model_validate(record.model_dump())
        if value.id not in self._table():
            raise Conflict("Cannot update a missing record")
        self._table()[value.id] = deepcopy(value)
        self.uow._dirty = True
        return deepcopy(value)

    def _page(self, query, predicate=lambda r: True, time_field=None, reverse=False):
        records = [r for r in self._table().values() if predicate(r)]
        if time_field:
            records = [r for r in records if
                       (query.from_at is None or getattr(r, time_field) >= query.from_at)
                       and (query.to is None or getattr(r, time_field) < query.to)]
        records.sort(key=lambda r: ((getattr(r, time_field), r.id) if time_field else r.id), reverse=reverse)
        return d.Page[self.model](items=deepcopy(records[query.offset:query.offset + query.limit]),
                                  total=len(records), limit=query.limit, offset=query.offset)

    def _add_many(self, records):
        # Validate the whole batch before modifying the working snapshot.
        values = [self.model.model_validate(r.model_dump()) for r in records]
        ids = [r.id for r in values]
        if len(ids) != len(set(ids)) or any(id in self._table() for id in ids):
            raise Conflict("Duplicate record ID in batch")
        for value in values:
            self._table()[value.id] = deepcopy(value)
        self.uow._dirty = self.uow._dirty or bool(values)
        return deepcopy(values)

    def _latest(self, predicate):
        result = {}
        for record in sorted(self._table().values(), key=lambda r: (r.observed_at, r.id)):
            if predicate(record):
                result[record.indicator] = deepcopy(record)
        return result


class MissionRepository(Records[d.Mission]):
    def get(self, id: d.UUIDString) -> d.Mission | None:
        return self._get(id)

    def list(self, query: d.MissionQuery) -> d.Page[d.Mission]:
        return self._page(query)

    def add(self, record: d.Mission) -> d.Mission:
        return self._add(record)


class AstronautRepository(Records[d.Astronaut]):
    def get(self, id: d.UUIDString) -> d.Astronaut | None:
        return self._get(id)

    def list(self, query: d.AstronautQuery) -> d.Page[d.Astronaut]:
        return self._page(query, lambda r: query.mission_id is None or r.mission_id == query.mission_id)

    def add(self, record: d.Astronaut) -> d.Astronaut:
        return self._add(record)


class CheckinRepository(Records[d.DailyCheckin]):
    def get(self, id: d.UUIDString) -> d.DailyCheckin | None:
        return self._get(id)

    def get_for_date(self, astronaut_id: d.UUIDString, date: date) -> d.DailyCheckin | None:
        return next((deepcopy(r) for r in self._table().values()
                     if r.astronaut_id == astronaut_id and r.checkin_date == date), None)

    def list(self, astronaut_id: d.UUIDString, query: d.CheckinQuery) -> d.Page[d.DailyCheckin]:
        return self._page(query, lambda r: r.astronaut_id == astronaut_id, "observed_at")

    def add(self, record: d.DailyCheckin) -> d.DailyCheckin:
        return self._add(record)


def reading_matches(record, owner_field, owner_id, query):
    return (getattr(record, owner_field) == owner_id
            and (query.indicator is None or record.indicator == query.indicator)
            and (query.source is None or record.source == query.source)
            and (query.simulation_run_id is None or record.simulation_run_id == query.simulation_run_id))


class HealthReadingRepository(Records[d.HealthReading]):
    def add_many(self, records: list[d.HealthReading]) -> list[d.HealthReading]:
        return self._add_many(records)

    def list(self, astronaut_id: d.UUIDString, query: d.HealthReadingQuery) -> d.Page[d.HealthReading]:
        return self._page(query, lambda r: reading_matches(r, "astronaut_id", astronaut_id, query), "observed_at")

    def latest_by_indicator(self, astronaut_id: d.UUIDString, source: Source | None = None) -> dict[HealthIndicator, d.HealthReading]:
        return self._latest(lambda r: r.astronaut_id == astronaut_id and (source is None or r.source == source))


class EnvironmentalReadingRepository(Records[d.EnvironmentalReading]):
    def add_many(self, records: list[d.EnvironmentalReading]) -> list[d.EnvironmentalReading]:
        return self._add_many(records)

    def list(self, mission_id: d.UUIDString, query: d.EnvironmentalReadingQuery) -> d.Page[d.EnvironmentalReading]:
        return self._page(query, lambda r: reading_matches(r, "mission_id", mission_id, query), "observed_at")

    def latest_by_indicator(self, mission_id: d.UUIDString) -> dict[EnvironmentalIndicator, d.EnvironmentalReading]:
        return self._latest(lambda r: r.mission_id == mission_id)


class AssessmentRepository(Records[d.Assessment]):
    def get(self, id: d.UUIDString) -> d.Assessment | None:
        return self._get(id)

    def get_by_fingerprint(self, astronaut_id: d.UUIDString, ruleset_version: str, fingerprint: str) -> d.Assessment | None:
        return next((deepcopy(r) for r in self._table().values() if
            (r.astronaut_id, r.ruleset_version, r.input_fingerprint) == (astronaut_id, ruleset_version, fingerprint)), None)

    def list(self, astronaut_id: d.UUIDString, query: d.AssessmentQuery) -> d.Page[d.Assessment]:
        return self._page(query, lambda r: r.astronaut_id == astronaut_id, "evaluated_at", reverse=True)

    def add(self, record: d.Assessment) -> d.Assessment:
        return self._add(record)


class AlertRepository(Records[d.Alert]):
    def get(self, id: d.UUIDString) -> d.Alert | None:
        return self._get(id)

    def list(self, astronaut_id: d.UUIDString, query: d.AlertQuery) -> d.Page[d.Alert]:
        records = [r for r in self._table().values() if r.astronaut_id == astronaut_id
                    and (query.state is None or r.state == query.state
                         or (query.state == AlertState.OPEN and r.state == AlertState.ACKNOWLEDGED))]
        records.sort(key=lambda r: (r.opened_at, r.id), reverse=True)
        return d.Page[d.Alert](items=deepcopy(records[query.offset:query.offset + query.limit]),
                               total=len(records), limit=query.limit, offset=query.offset)

    def get_open(self, astronaut_id: d.UUIDString, rule_id: str) -> d.Alert | None:
        return next((deepcopy(r) for r in self._table().values() if r.astronaut_id == astronaut_id
                     and r.rule_id == rule_id and r.state != AlertState.RESOLVED), None)

    def add(self, record: d.Alert) -> d.Alert:
        return self._add(record)

    def update(self, record: d.Alert) -> d.Alert:
        return self._update(record)


class SimulationRunRepository(Records[d.SimulationRun]):
    def get(self, id: d.UUIDString) -> d.SimulationRun | None:
        return self._get(id)

    def get_active(self) -> d.SimulationRun | None:
        return next((deepcopy(r) for r in self._table().values()
                     if r.status in (RunStatus.PAUSED, RunStatus.RUNNING)), None)

    def list(self, query: d.SimulationRunQuery) -> d.Page[d.SimulationRun]:
        return self._page(query, lambda r: query.status is None or r.status == query.status)

    def add(self, record: d.SimulationRun) -> d.SimulationRun:
        return self._add(record)

    def update(self, record: d.SimulationRun, expected_last_tick: int) -> d.SimulationRun:
        previous = self._get(record.id)
        if previous is None or previous.last_tick_index != expected_last_tick:
            raise ConcurrentWrite("Simulation progress changed")
        return self._update(record)


class CommandReceiptRepository(Records[d.CommandReceipt]):
    def get(self, command_id: d.UUIDString) -> d.CommandReceipt | None:
        return self._get(command_id)

    def add(self, record: d.CommandReceipt) -> d.CommandReceipt:
        return self._add(record)


class MemoryUnitOfWork:
    def __init__(self, factory):
        self._factory = factory
        self._active = False
        for name, repository, model in (
            ("missions", MissionRepository, d.Mission), ("astronauts", AstronautRepository, d.Astronaut),
            ("checkins", CheckinRepository, d.DailyCheckin), ("health_readings", HealthReadingRepository, d.HealthReading),
            ("environmental_readings", EnvironmentalReadingRepository, d.EnvironmentalReading),
            ("assessments", AssessmentRepository, d.Assessment), ("alerts", AlertRepository, d.Alert),
            ("simulation_runs", SimulationRunRepository, d.SimulationRun),
            ("command_receipts", CommandReceiptRepository, d.CommandReceipt),
        ):
            setattr(self, name, repository(self, name, model))

    def _ensure_active(self):
        if not self._active or self._factory._closed:
            raise RepositoryUnavailable("Unit of work is not active")

    def __enter__(self) -> "MemoryUnitOfWork":
        if self._active:
            raise Conflict("Unit of work already active")
        with self._factory._lock:
            if self._factory._closed:
                raise RepositoryUnavailable("Memory adapter is closed")
            self._state = deepcopy(self._factory._state)
            self._revision = self._factory._revision
        self._dirty = False
        self._active = True
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None) -> None:
        try:
            self.rollback()
        finally:
            self._active = False
            self._state = None

    def commit(self) -> None:
        self._ensure_active()
        if not self._dirty:
            return
        with self._factory._lock:
            if self._factory._revision != self._revision:
                raise ConcurrentWrite("Memory store changed since transaction began")
            validate_state(self._state)
            self._factory._state = deepcopy(self._state)
            self._factory._revision += 1
            self._revision = self._factory._revision
            self._dirty = False

    def rollback(self) -> None:
        self._ensure_active()
        with self._factory._lock:
            self._state = deepcopy(self._factory._state)
            self._revision = self._factory._revision
            self._dirty = False
