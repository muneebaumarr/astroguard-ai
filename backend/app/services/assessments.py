"""Service-level assessment/alert writes share their caller's transaction."""
from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID, uuid5

from astroguard_contracts import dto as d
from astroguard_contracts.errors import ConcurrentWrite
from .errors import CheckinConflict, IdempotencyConflict, ResourceNotFound
from .initial_assessment import evaluate


def all_alerts(uow, astronaut_id):
    records, offset = [], 0
    while True:
        page = uow.alerts.list(astronaut_id, d.AlertQuery(limit=1000, offset=offset))
        records.extend(page.items)
        offset += len(page.items)
        if offset >= page.total:
            return records


def persist(uow, assessment):
    existing = uow.assessments.get_by_fingerprint(assessment.astronaut_id, assessment.ruleset_version, assessment.input_fingerprint)
    if existing:
        return existing, []
    assessment = uow.assessments.add(assessment)
    created = []
    for result in assessment.results:
        alert = uow.alerts.get_open(assessment.astronaut_id, result.rule_id)
        if alert and result.evidence:
            previous = uow.assessments.get(alert.latest_assessment_id)
            previous_rule = next((r for r in previous.results if r.rule_id == result.rule_id), None) if previous else None
            if previous_rule and previous_rule.evidence and max(e.observed_at for e in result.evidence) < max(e.observed_at for e in previous_rule.evidence):
                # Saving an older observation is not new evidence that clears a newer flag.
                continue
        if result.outcome == "triggered":
            if alert:
                uow.alerts.update(d.Alert.model_validate(alert.model_dump() | {"latest_assessment_id": assessment.id, "workflow_status": result.workflow_status}))
            else:
                alert = d.Alert(id=str(uuid5(UUID(assessment.id), result.rule_id)), created_at=assessment.created_at,
                    astronaut_id=assessment.astronaut_id, rule_id=result.rule_id, workflow_status=result.workflow_status,
                    state="open", first_assessment_id=assessment.id, latest_assessment_id=assessment.id, opened_at=assessment.evaluated_at)
                created.append(uow.alerts.add(alert))
        elif result.outcome == "not_triggered" and alert:
            uow.alerts.update(d.Alert.model_validate(alert.model_dump() | {"latest_assessment_id": assessment.id,
                "state": "resolved", "resolved_at": max(assessment.evaluated_at, alert.opened_at)}))
    return assessment, sorted(created, key=lambda a: a.rule_id)


def original_created_alerts(uow, assessment):
    """Replay immutable creation snapshots even after later lifecycle changes."""
    results = {r.rule_id: r for r in assessment.results}
    return [d.Alert.model_validate(alert.model_dump() | {"state": "open", "latest_assessment_id": assessment.id,
        "acknowledged_at": None, "resolved_at": None, "workflow_status": results[alert.rule_id].workflow_status})
        for alert in sorted(all_alerts(uow, assessment.astronaut_id), key=lambda a: a.rule_id)
        if alert.first_assessment_id == assessment.id]


class AssessmentService:
    def __init__(self, adapter):
        self.adapter = adapter

    def command(self, astronaut_id, key, alert_id=None):
        operation = f"ack_alert:{astronaut_id}:{alert_id}" if alert_id else f"evaluate:{astronaut_id}"
        digest = sha256(operation.encode()).hexdigest()
        for attempt in range(3):
            try:
                with self.adapter.create_uow() as uow:
                    astronaut = uow.astronauts.get(astronaut_id)
                    if astronaut is None:
                        raise ResourceNotFound("Astronaut not found")
                    receipt = uow.command_receipts.get(key)
                    if receipt:
                        if (receipt.operation != operation and not (alert_id and receipt.operation.startswith(operation + "|"))) or receipt.request_hash != digest:
                            raise IdempotencyConflict("Idempotency key belongs to another command")
                        if not alert_id:
                            return uow.assessments.get(receipt.result_id)
                        # Replay the acknowledged revision even if subsequent data resolves it.
                        alert = uow.alerts.get(receipt.result_id)
                        return self._ack_snapshot(uow, receipt, alert)
                    now = datetime.now(timezone.utc)
                    if alert_id:
                        alert = uow.alerts.get(alert_id)
                        if alert is None or alert.astronaut_id != astronaut_id:
                            raise ResourceNotFound("Alert not found for this astronaut")
                        if alert.state == "resolved":
                            raise CheckinConflict("A resolved alert cannot be acknowledged")
                        result = d.Alert.model_validate(alert.model_dump() | {"state": "acknowledged", "acknowledged_at": alert.acknowledged_at or max(now, alert.opened_at)})
                        result = uow.alerts.update(result)
                        # Receipt metadata retains the immutable revision for exact replay.
                        snapshot = f"{result.latest_assessment_id}|{result.workflow_status}"
                    else:
                        latest = uow.checkins.list(astronaut_id, d.CheckinQuery(limit=1000))
                        records = list(latest.items)
                        offset = len(records)
                        while offset < latest.total:
                            page = uow.checkins.list(astronaut_id, d.CheckinQuery(limit=1000, offset=offset))
                            records.extend(page.items); offset += len(page.items)
                        checkin = max(records, key=lambda c: (c.observed_at, c.id), default=None)
                        result, _ = persist(uow, evaluate(astronaut_id, list(uow.health_readings.latest_by_indicator(astronaut_id).values()),
                            list(uow.environmental_readings.latest_by_indicator(astronaut.mission_id).values()), checkin, now))
                        snapshot = ""
                    uow.command_receipts.add(d.CommandReceipt(id=key, created_at=now, operation=operation + ("|" + snapshot if snapshot else ""), request_hash=digest,
                        result_type="alert" if alert_id else "assessment", result_id=result.id))
                    uow.commit()
                    return result
            except ConcurrentWrite:
                if attempt == 2:
                    raise

    @staticmethod
    def _ack_snapshot(uow, receipt, alert):
        _, assessment_id, status = receipt.operation.rsplit("|", 2)
        return d.Alert.model_validate(alert.model_dump() | {"state": "acknowledged", "resolved_at": None,
            "latest_assessment_id": assessment_id, "workflow_status": status})
