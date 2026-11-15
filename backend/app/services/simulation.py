from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import UUID, uuid5

from astroguard_contracts import dto as d
from astroguard_contracts.errors import ConcurrentWrite, RepositoryUnavailable
from astroguard_contracts.repositories import AdapterFactory

from app.simulation.generator import VERSION, generate_tick
from .errors import CheckinConflict, IdempotencyConflict, ResourceNotFound


class InvalidTransition(CheckinConflict):
    code = "invalid_transition"


class SimulationService:
    def __init__(self, adapter: AdapterFactory):
        self.adapter = adapter

    @staticmethod
    def _run(uow, id):
        value = uow.simulation_runs.get(id)
        if value is None:
            raise ResourceNotFound("Simulation run not found")
        return value

    def _command(self, action, target, payload, key, execute):
        digest = sha256(json.dumps([action, target, payload], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        prefix = f"simulation.{action}|"
        for attempt in range(3):
            try:
                with self.adapter.create_uow() as uow:
                    receipt = uow.command_receipts.get(key)
                    if receipt:
                        if receipt.request_hash != digest or not receipt.operation.startswith(prefix):
                            raise IdempotencyConflict("This idempotency key belongs to a different command.")
                        # Run configuration is immutable. The existing operation string
                        # retains compact revision metadata for exact response replay,
                        # without a new DTO, table or adapter-specific response cache.
                        tick, status, started = json.loads(receipt.operation[len(prefix):])
                        stored = self._run(uow, receipt.result_id)
                        run = d.SimulationRun.model_validate(stored.model_dump() | {
                            "last_tick_index": tick, "status": status, "started_at": started, "last_error": None})
                        if action == "steps":
                            return d.SimulationStepResult(run=run, generated_health_count=payload["steps"] * 3,
                                generated_environmental_count=payload["steps"] * 2)
                        return run
                    now = datetime.now(timezone.utc)
                    result = execute(uow, now)
                    run = result.run if isinstance(result, d.SimulationStepResult) else result
                    snapshot = [run.last_tick_index, run.status, run.started_at.isoformat() if run.started_at else None]
                    uow.command_receipts.add(d.CommandReceipt(id=key, created_at=now, operation=prefix + json.dumps(snapshot, separators=(",", ":")),
                        request_hash=digest, result_type="simulation_run", result_id=run.id))
                    uow.commit()
                    return result
            except ConcurrentWrite:
                if attempt == 2:
                    raise
        raise AssertionError("unreachable")

    def create(self, request: d.SimulationRunCreate, key: str):
        def execute(uow, now):
            astronaut = uow.astronauts.get(request.astronaut_id)
            if astronaut is None:
                raise ResourceNotFound("Astronaut not found")
            if uow.simulation_runs.get_active() is not None:
                raise CheckinConflict("Another simulation is active. Stop it before starting a new run.")
            return uow.simulation_runs.add(d.SimulationRun(id=str(uuid5(UUID(key), "simulation.run")), created_at=now,
                mission_id=astronaut.mission_id, scenario_version=VERSION, **request.model_dump()))
        return self._command("create", request.astronaut_id, request.model_dump(mode="json"), key, execute)

    def steps(self, id: str, request: d.SimulationSteps, key: str):
        def execute(uow, now):
            run = self._run(uow, id)
            if run.status != "paused":
                raise InvalidTransition("Explicit ticks require a paused run. Pause it first.")
            health, environment = [], []
            try:
                for tick in range(run.last_tick_index + 1, run.last_tick_index + request.steps + 1):
                    h, e = generate_tick(run, tick, now)
                    health.extend(h)
                    environment.extend(e)
            except (OverflowError, ValueError) as exc:
                raise InvalidTransition("The run version or simulation timestamp cannot be advanced.") from exc
            uow.health_readings.add_many(health)
            uow.environmental_readings.add_many(environment)
            updated = d.SimulationRun.model_validate(run.model_dump() | {
                "last_tick_index": run.last_tick_index + request.steps, "started_at": run.started_at or now})
            updated = uow.simulation_runs.update(updated, expected_last_tick=run.last_tick_index)
            return d.SimulationStepResult(run=updated, generated_health_count=len(health), generated_environmental_count=len(environment))
        return self._command("steps", id, request.model_dump(mode="json"), key, execute)

    def control(self, id: str, action: str, key: str):
        def execute(uow, now):
            run = self._run(uow, id)
            if run.status in ("stopped", "failed"):
                if action == "stop" and run.status == "stopped":
                    return run
                raise InvalidTransition("Stopped or failed runs cannot be resumed or paused.")
            status = {"pause": "paused", "resume": "running", "stop": "stopped"}[action]
            updated = d.SimulationRun.model_validate(run.model_dump() | {
                "status": status, "started_at": run.started_at or (now if action == "resume" else None)})
            return uow.simulation_runs.update(updated, expected_last_tick=run.last_tick_index)
        return self._command(action, id, {}, key, execute)

    def get(self, id):
        with self.adapter.create_uow() as uow:
            return self._run(uow, id)

    def list(self, query: d.SimulationRunQuery):
        with self.adapter.create_uow() as uow:
            return uow.simulation_runs.list(query)

    def health(self, astronaut_id):
        with self.adapter.create_uow() as uow:
            if uow.astronauts.get(astronaut_id) is None:
                raise ResourceNotFound("Astronaut not found")
            return d.HealthTelemetry(astronaut_id=astronaut_id, as_of=datetime.now(timezone.utc),
                readings=list(uow.health_readings.latest_by_indicator(astronaut_id, source="simulated").values()))

    def environment(self, mission_id, query=None):
        with self.adapter.create_uow() as uow:
            if uow.missions.get(mission_id) is None:
                raise ResourceNotFound("Mission not found")
            if query is not None:
                return uow.environmental_readings.list(mission_id, query)
            return d.EnvironmentalTelemetry(mission_id=mission_id, as_of=datetime.now(timezone.utc),
                readings=list(uow.environmental_readings.latest_by_indicator(mission_id).values()))
