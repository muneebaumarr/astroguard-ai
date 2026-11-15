from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from uuid import UUID, uuid5

from astroguard_contracts import dto as d
from astroguard_contracts.errors import Conflict, RepositoryUnavailable
from astroguard_contracts.repositories import AdapterFactory, UnitOfWork

from .errors import CheckinConflict, IdempotencyConflict, ResourceNotFound
from .initial_assessment import assess_checkin, assessment_id_for
from .assessments import persist, original_created_alerts


class CheckinService:
    def __init__(self, adapter: AdapterFactory):
        self.adapter = adapter

    @staticmethod
    def require_astronaut(uow: UnitOfWork, astronaut_id: str) -> None:
        if uow.astronauts.get(astronaut_id) is None:
            raise ResourceNotFound("Astronaut not found")

    def create(self, astronaut_id: str, request: d.CheckinCreate, command_id: str) -> d.CheckinResult:
        payload = request.model_dump(mode="json")
        payload["readings"] = sorted(payload["readings"], key=lambda r: r["indicator"])
        operation = f"create_checkin:{astronaut_id}"
        digest = sha256(json.dumps({"astronaut_id": astronaut_id, "checkin": payload},
            sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        # Retry a lost optimistic race from a new snapshot, including simultaneous
        # requests with the same command UUID. No adapter-specific state is accessed.
        for attempt in range(3):
            try:
                with self.adapter.create_uow() as uow:
                    receipt = uow.command_receipts.get(command_id)
                    if receipt is not None:
                        if receipt.operation != operation or receipt.request_hash != digest:
                            raise IdempotencyConflict("This idempotency key was already used for a different command. Use a new key for new data.")
                        return self._replay(uow, astronaut_id, receipt.result_id)
                    self.require_astronaut(uow, astronaut_id)
                    if uow.checkins.get_for_date(astronaut_id, request.checkin_date) is not None:
                        raise CheckinConflict("A check-in already exists for this astronaut on this UTC date. Choose another date; editing is not available.")
                    now = datetime.now(timezone.utc)
                    checkin_id = str(uuid5(UUID(command_id), operation))
                    checkin = d.DailyCheckin(id=checkin_id, created_at=now, astronaut_id=astronaut_id, **payload)
                    checkin = uow.checkins.add(checkin)
                    readings = [d.HealthReading(id=str(uuid5(UUID(checkin_id), value.indicator)),
                        created_at=now, astronaut_id=astronaut_id, observed_at=checkin.observed_at,
                        source="manual", context=checkin.context, checkin_id=checkin_id,
                        **value.model_dump()) for value in checkin.readings]
                    readings = uow.health_readings.add_many(readings)
                    assessment, alerts = persist(uow, assess_checkin(checkin, readings))
                    uow.command_receipts.add(d.CommandReceipt(id=command_id, created_at=now,
                        operation=operation, request_hash=digest, result_type="daily_checkin", result_id=checkin_id))
                    result = d.CheckinResult(checkin=checkin, readings=readings, assessment=assessment, alerts=alerts)
                    uow.commit()
                    return result
            except Conflict as exc:
                # A competing SQL transaction may commit this command between our
                # receipt lookup and insert. Reopen the transaction and replay it.
                if isinstance(exc, CheckinConflict) or attempt == 2:
                    raise
        raise AssertionError("unreachable")

    def _replay(self, uow, astronaut_id, checkin_id):
        checkin = uow.checkins.get(checkin_id)
        assessment = uow.assessments.get(assessment_id_for(checkin_id))
        if checkin is None or assessment is None or checkin.astronaut_id != astronaut_id:
            raise RepositoryUnavailable("Stored command result is incomplete")
        query_values = {"from": checkin.observed_at, "to": checkin.observed_at + timedelta(microseconds=1),
                        "source": "manual", "limit": 1000}
        readings, offset = [], 0
        while True:
            page = uow.health_readings.list(astronaut_id, d.HealthReadingQuery.model_validate(query_values | {"offset": offset}))
            readings.extend(r for r in page.items if r.checkin_id == checkin_id)
            offset += len(page.items)
            if offset >= page.total:
                break
            if not page.items:
                raise RepositoryUnavailable("Stored reading page is incomplete")
        readings.sort(key=lambda r: r.indicator)
        if [(r.indicator, r.value, r.unit) for r in readings] != [
            (r.indicator, r.value, r.unit) for r in sorted(checkin.readings, key=lambda r: r.indicator)
        ]:
            raise RepositoryUnavailable("Stored command measurements are incomplete")
        return d.CheckinResult(checkin=checkin, readings=readings, assessment=assessment, alerts=original_created_alerts(uow, assessment))

    def list(self, astronaut_id: str, query: d.CheckinQuery) -> d.Page[d.DailyCheckin]:
        with self.adapter.create_uow() as uow:
            self.require_astronaut(uow, astronaut_id)
            return uow.checkins.list(astronaut_id, query)

    def get(self, astronaut_id: str, checkin_id: str) -> d.DailyCheckin:
        with self.adapter.create_uow() as uow:
            self.require_astronaut(uow, astronaut_id)
            record = uow.checkins.get(checkin_id)
            if record is None or record.astronaut_id != astronaut_id:
                raise ResourceNotFound("Check-in not found for this astronaut")
            return record

    def readings(self, astronaut_id: str, query: d.HealthReadingQuery) -> d.Page[d.HealthReading]:
        with self.adapter.create_uow() as uow:
            self.require_astronaut(uow, astronaut_id)
            return uow.health_readings.list(astronaut_id, query)

    def assessments(self, astronaut_id: str, query: d.AssessmentQuery) -> d.Page[d.Assessment]:
        with self.adapter.create_uow() as uow:
            self.require_astronaut(uow, astronaut_id)
            return uow.assessments.list(astronaut_id, query)

    def assessment(self, astronaut_id: str, assessment_id: str) -> d.Assessment:
        with self.adapter.create_uow() as uow:
            self.require_astronaut(uow, astronaut_id)
            record = uow.assessments.get(assessment_id)
            if record is None or record.astronaut_id != astronaut_id:
                raise ResourceNotFound("Assessment not found for this astronaut")
            return record
