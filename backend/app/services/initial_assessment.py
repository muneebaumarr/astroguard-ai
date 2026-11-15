"""Deterministic educational input review, not a clinical scoring engine."""
from hashlib import sha256
from uuid import UUID, uuid5

from astroguard_contracts import dto as d

RULESET_VERSION = "checkin-demo-v1"


def assessment_id_for(checkin_id: str) -> str:
    return str(uuid5(UUID(checkin_id), RULESET_VERSION))


def assess_checkin(checkin: d.DailyCheckin, readings: list[d.HealthReading]) -> d.Assessment:
    evidence = [d.Evidence(record_id=r.id, record_type="health_reading", observed_at=r.observed_at,
                           indicator=r.indicator, value=r.value, unit=r.unit) for r in readings]
    for field, unit in (("sleep_hours", "h"), ("mood", "scale_1_5"), ("stress", "scale_1_5"), ("exercise_minutes", "min")):
        value = getattr(checkin, field)
        if value is not None:
            evidence.append(d.Evidence(record_id=checkin.id, record_type="daily_checkin",
                observed_at=checkin.observed_at, indicator=field, value=value, unit=unit))
    # Always link the assessment to its check-in, including notes-only submissions.
    evidence.append(d.Evidence(record_id=checkin.id, record_type="daily_checkin",
        observed_at=checkin.observed_at, indicator="reported_symptom_count",
        value=len(checkin.symptoms), unit="count"))
    review = bool(checkin.symptoms)
    status = "review_suggested" if review else "insufficient_data"
    supplied = len(readings) + sum(getattr(checkin, field) is not None
        for field in ("sleep_hours", "mood", "stress", "exercise_minutes"))
    results = [d.RuleResult(rule_id="reported_symptoms", outcome="triggered" if review else "not_triggered",
        workflow_status="review_suggested" if review else "insufficient_data",
        explanation=(f"You recorded {len(checkin.symptoms)} symptom entries. This educational flag marks your report for review; it does not determine severity."
                     if review else "No symptom entries were supplied. This does not establish that symptoms are absent or that your health is reassuring."),
        evidence=[evidence[-1]]),
        d.RuleResult(rule_id="clinical_context", outcome="insufficient_data", workflow_status="insufficient_data",
            explanation=f"Recorded {supplied} numeric observations, {len(checkin.symptoms)} symptom entries and {'a note' if checkin.notes else 'no note'}. Clinical evaluation is not implemented; omitted fields remain unknown.",
            evidence=evidence, missing_data=["Validated clinical rules and mission-specific context are not available."])]
    fingerprint = sha256(checkin.model_dump_json().encode()).hexdigest()
    return d.Assessment(id=assessment_id_for(checkin.id), created_at=checkin.created_at,
        astronaut_id=checkin.astronaut_id, evaluated_at=checkin.created_at, status=status,
        ruleset_version=RULESET_VERSION, input_fingerprint=fingerprint,
        coverage=d.Coverage(evaluated_rule_ids=["reported_symptoms"], insufficient_rule_ids=["clinical_context"]),
        results=results)
