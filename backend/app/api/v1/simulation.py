from typing import Annotated

from fastapi import APIRouter, Depends
from astroguard_contracts import dto as d
from astroguard_contracts.enums import EnvironmentalIndicator, RunStatus, Source

from app.services.simulation import SimulationService
from app.simulation.generator import scenarios
from .checkins import Adapter, CommandID, checkin_query
from .routes import Limit, Offset

router = APIRouter()


@router.get("/simulation/scenarios", response_model=d.Page[d.ScenarioDefinition])
def list_scenarios(limit: Limit = 100, offset: Offset = 0):
    values = scenarios()
    return d.Page[d.ScenarioDefinition](items=values[offset:offset + limit], total=len(values), limit=limit, offset=offset)


@router.get("/simulation/runs", response_model=d.Page[d.SimulationRun])
def list_runs(adapter: Adapter, status: RunStatus | None = None, limit: Limit = 100, offset: Offset = 0):
    return SimulationService(adapter).list(d.SimulationRunQuery(status=status, limit=limit, offset=offset))


@router.post("/simulation/runs", response_model=d.SimulationRun, status_code=201)
def create_run(body: d.SimulationRunCreate, command_id: CommandID, adapter: Adapter):
    return SimulationService(adapter).create(body, command_id)


@router.get("/simulation/runs/{id}", response_model=d.SimulationRun)
def get_run(id: d.UUIDString, adapter: Adapter):
    return SimulationService(adapter).get(id)


@router.post("/simulation/runs/{id}/steps", response_model=d.SimulationStepResult)
def steps(id: d.UUIDString, body: d.SimulationSteps, command_id: CommandID, adapter: Adapter):
    return SimulationService(adapter).steps(id, body, command_id)


@router.post("/simulation/runs/{id}/pause", response_model=d.SimulationRun)
def pause(id: d.UUIDString, command_id: CommandID, adapter: Adapter):
    return SimulationService(adapter).control(id, "pause", command_id)


@router.post("/simulation/runs/{id}/resume", response_model=d.SimulationRun)
def resume(id: d.UUIDString, command_id: CommandID, adapter: Adapter):
    return SimulationService(adapter).control(id, "resume", command_id)


@router.post("/simulation/runs/{id}/stop", response_model=d.SimulationRun)
def stop(id: d.UUIDString, command_id: CommandID, adapter: Adapter):
    return SimulationService(adapter).control(id, "stop", command_id)


@router.get("/astronauts/{id}/telemetry/latest", response_model=d.HealthTelemetry)
def health_telemetry(id: d.UUIDString, adapter: Adapter):
    return SimulationService(adapter).health(id)


@router.get("/missions/{id}/telemetry/latest", response_model=d.EnvironmentalTelemetry)
def environmental_telemetry(id: d.UUIDString, adapter: Adapter):
    return SimulationService(adapter).environment(id)


@router.get("/missions/{id}/environmental-readings", response_model=d.Page[d.EnvironmentalReading])
def environmental_readings(id: d.UUIDString, adapter: Adapter,
    time: Annotated[d.CheckinQuery, Depends(checkin_query)], indicator: EnvironmentalIndicator | None = None,
    source: Source | None = None, simulation_run_id: d.UUIDString | None = None):
    # The shared environmental query accepts simulated source only.
    from fastapi.exceptions import RequestValidationError
    from pydantic import ValidationError
    try:
        query = d.EnvironmentalReadingQuery.model_validate(time.model_dump(by_alias=True) | {
            "indicator": indicator, "source": source, "simulation_run_id": simulation_run_id})
    except ValidationError as exc:
        raise RequestValidationError([{**error, "loc": ("query", *error["loc"])} for error in exc.errors()]) from exc
    return SimulationService(adapter).environment(id, query)
