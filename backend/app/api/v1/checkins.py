from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from astroguard_contracts import dto as d
from astroguard_contracts.enums import HealthIndicator, Source, AlertState
from astroguard_contracts.repositories import AdapterFactory

from app.api.dependencies import get_adapter
from app.services.checkins import CheckinService
from app.services.assessments import AssessmentService
from .routes import Limit, Offset

router = APIRouter()
Adapter = Annotated[AdapterFactory, Depends(get_adapter)]
CommandID = Annotated[d.UUIDString, Header(alias="Idempotency-Key")]


def checkin_query(limit: Limit = 100, offset: Offset = 0,
                  from_at: Annotated[d.UTCDateTime | None, Query(alias="from")] = None,
                  to: d.UTCDateTime | None = None) -> d.CheckinQuery:
    try:
        return d.CheckinQuery.model_validate({"limit": limit, "offset": offset, "from": from_at, "to": to})
    except ValidationError as exc:
        raise RequestValidationError([{**error, "loc": ("query", *error["loc"])} for error in exc.errors()]) from exc


@router.post("/astronauts/{id}/checkins", response_model=d.CheckinResult, status_code=201)
def create_checkin(id: d.UUIDString, body: d.CheckinCreate, command_id: CommandID, adapter: Adapter):
    return CheckinService(adapter).create(id, body, command_id)


@router.get("/astronauts/{id}/checkins", response_model=d.Page[d.DailyCheckin])
def list_checkins(id: d.UUIDString, adapter: Adapter, query: Annotated[d.CheckinQuery, Depends(checkin_query)]):
    return CheckinService(adapter).list(id, query)


@router.get("/astronauts/{id}/checkins/{checkin_id}", response_model=d.DailyCheckin)
def get_checkin(id: d.UUIDString, checkin_id: d.UUIDString, adapter: Adapter):
    return CheckinService(adapter).get(id, checkin_id)


@router.get("/astronauts/{id}/readings", response_model=d.Page[d.HealthReading])
def readings(id: d.UUIDString, adapter: Adapter,
             time: Annotated[d.CheckinQuery, Depends(checkin_query)],
             indicator: HealthIndicator | None = None, source: Source | None = None,
             simulation_run_id: d.UUIDString | None = None):
    query = d.HealthReadingQuery.model_validate(time.model_dump(by_alias=True) | {
        "indicator": indicator, "source": source, "simulation_run_id": simulation_run_id})
    return CheckinService(adapter).readings(id, query)


@router.get("/astronauts/{id}/assessments", response_model=d.Page[d.Assessment])
def assessments(id: d.UUIDString, adapter: Adapter,
                time: Annotated[d.CheckinQuery, Depends(checkin_query)]):
    return CheckinService(adapter).assessments(id, d.AssessmentQuery.model_validate(time.model_dump(by_alias=True)))


@router.get("/astronauts/{id}/assessments/{assessment_id}", response_model=d.Assessment)
def assessment(id: d.UUIDString, assessment_id: d.UUIDString, adapter: Adapter):
    return CheckinService(adapter).assessment(id, assessment_id)


@router.post("/astronauts/{id}/assessments", response_model=d.Assessment)
def evaluate_observations(id: d.UUIDString, command_id: CommandID, adapter: Adapter):
    return AssessmentService(adapter).command(id, command_id)


@router.get("/astronauts/{id}/alerts", response_model=d.Page[d.Alert])
def alerts(id: d.UUIDString, adapter: Adapter, state: AlertState | None = None, limit: Limit = 100, offset: Offset = 0):
    with adapter.create_uow() as uow:
        CheckinService.require_astronaut(uow, id)
        return uow.alerts.list(id, d.AlertQuery(state=state, limit=limit, offset=offset))


@router.post("/astronauts/{id}/alerts/{alert_id}/acknowledgement", response_model=d.Alert)
def acknowledge(id: d.UUIDString, alert_id: d.UUIDString, command_id: CommandID, adapter: Adapter):
    return AssessmentService(adapter).command(id, command_id, alert_id)
