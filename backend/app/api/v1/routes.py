from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from astroguard_contracts import CONTRACT_VERSION, dto as d
from astroguard_contracts.repositories import AdapterFactory, UnitOfWork

from app.api.dependencies import get_adapter, get_uow
from app.services.profiles import ProfileService

router = APIRouter()
Uow = Annotated[UnitOfWork, Depends(get_uow)]
Adapter = Annotated[AdapterFactory, Depends(get_adapter)]
Limit = Annotated[int, Query(ge=1, le=1000)]
Offset = Annotated[int, Query(ge=0)]


@router.get("/health", response_model=d.HealthResponse)
def health(adapter: Adapter):
    return d.HealthResponse(contract_version=CONTRACT_VERSION, adapter=adapter.check_ready().adapter)


@router.get("/ready", response_model=d.ReadinessResult,
            responses={503: {"model": d.ReadinessResult}})
def ready(adapter: Adapter, response: Response):
    result = adapter.check_ready()
    if not result.ready:
        response.status_code = 503
    return result


@router.get("/missions", response_model=d.Page[d.Mission])
def missions(uow: Uow, limit: Limit = 100, offset: Offset = 0):
    return ProfileService(uow).missions(d.MissionQuery(limit=limit, offset=offset))


@router.get("/missions/{id}", response_model=d.Mission)
def mission(id: d.UUIDString, uow: Uow):
    record = ProfileService(uow).mission(id)
    if record is None:
        raise HTTPException(404, "Mission not found")
    return record


@router.get("/astronauts", response_model=d.Page[d.Astronaut])
def astronauts(uow: Uow, limit: Limit = 100, offset: Offset = 0, mission_id: d.UUIDString | None = None):
    return ProfileService(uow).astronauts(d.AstronautQuery(limit=limit, offset=offset, mission_id=mission_id))


@router.get("/astronauts/{id}", response_model=d.Astronaut)
def astronaut(id: d.UUIDString, uow: Uow):
    record = ProfileService(uow).astronaut(id)
    if record is None:
        raise HTTPException(404, "Astronaut not found")
    return record
