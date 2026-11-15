"""Pure, deterministic demonstration rules; no clinical or agency-approved thresholds."""
from hashlib import sha256
import json
from uuid import UUID, uuid5

from astroguard_contracts import dto as d

RULESET_VERSION = "educational-demo-v2"
DISCLAIMER = "Educational fictional rules only. No diagnosis, emergency prediction, clinical validation or safety clearance."
# (rule, indicator, direction, review boundary, elevated boundary, unit, source)
RULES = (
    ("demo_heart_rate", "heart_rate", "high", 110, 125, "bpm", "health_reading"),
    ("demo_oxygen", "spo2", "low", 95, 92, "%", "health_reading"),
    ("demo_temperature", "body_temperature", "high", 37.8, 38.5, "degC", "health_reading"),
    ("demo_cabin_co2", "cabin_co2", "high", 1200, 1800, "ppm", "environmental_reading"),
    ("demo_radiation", "radiation_dose_rate", "high", 20, 35, "uSv/h", "environmental_reading"),
    ("demo_sleep", "sleep_hours", "low_strict", 6, 4, "h", "daily_checkin"),
    ("demo_stress", "stress", "high", 4, 5, "scale_1_5", "daily_checkin"),
    ("demo_mood", "mood", "low", 2, 1, "scale_1_5", "daily_checkin"),
)


def assessment_id_for(checkin_id: str) -> str:
    return str(uuid5(UUID(checkin_id), RULESET_VERSION))


def evaluate(astronaut_id, health, environment, checkin, now, assessment_id=None):
    evidence = {}
    for kind, records in (("health_reading", health), ("environmental_reading", environment)):
        for reading in sorted(records, key=lambda r: (r.observed_at, r.id)):
            evidence[reading.indicator] = d.Evidence(record_id=reading.id, record_type=kind,
                observed_at=reading.observed_at, indicator=reading.indicator, value=reading.value, unit=reading.unit)
    if checkin:
        for field, unit in (("sleep_hours", "h"), ("stress", "scale_1_5"), ("mood", "scale_1_5"), ("exercise_minutes", "min")):
            value = getattr(checkin, field)
            if value is not None:
                evidence[field] = d.Evidence(record_id=checkin.id, record_type="daily_checkin", observed_at=checkin.observed_at,
                    indicator=field, value=value, unit=unit)
        evidence["reported_symptom_count"] = d.Evidence(record_id=checkin.id, record_type="daily_checkin", observed_at=checkin.observed_at,
            indicator="reported_symptom_count", value=len(checkin.symptoms), unit="count")
    results = []
    for rule, indicator, direction, review, elevated, unit, kind in RULES:
        item = evidence.get(indicator)
        if item is None:
            results.append(d.RuleResult(rule_id=rule, outcome="insufficient_data", workflow_status="insufficient_data",
                explanation=f"No {indicator} supplied; this demonstration rule cannot evaluate missing data.", missing_data=[indicator]))
            continue
        compare = (lambda boundary: item.value >= boundary) if direction == "high" else (lambda boundary: item.value < boundary) if direction == "low_strict" else (lambda boundary: item.value <= boundary)
        triggered, stronger = compare(review), compare(elevated)
        operator = ">=" if direction == "high" else "<" if direction == "low_strict" else "<="
        results.append(d.RuleResult(rule_id=rule, outcome="triggered" if triggered else "not_triggered",
            workflow_status="crew_medical_review" if stronger else "review_suggested" if triggered else "no_rule_triggered",
            explanation=f"Fictional demo: {indicator}={item.value:g} {unit}; review at {operator}{review}, elevated review at {operator}{elevated}. Not a clinical threshold.", evidence=[item]))
    symptom = evidence.get("reported_symptom_count")
    count = len(checkin.symptoms) if checkin else None
    results.append(d.RuleResult(rule_id="reported_symptoms", outcome="insufficient_data" if count is None else "triggered" if count else "not_triggered",
        workflow_status="insufficient_data" if count is None else "crew_medical_review" if count >= 3 else "review_suggested" if count else "no_rule_triggered",
        explanation=("No check-in supplied; symptoms remain unknown." if count is None else
            f"Fictional demo: {count} reported symptom entries; review at 1, elevated review at 3. Report: {', '.join(checkin.symptoms)[:65] or 'none supplied'}. No diagnosis."),
        evidence=[symptom] if symptom else [], missing_data=["daily_checkin"] if count is None else []))
    results.append(d.RuleResult(rule_id="clinical_context", outcome="insufficient_data", workflow_status="insufficient_data",
        explanation="Clinical evaluation is not implemented. Demo boundaries are authored for fictional scenarios; missing observations remain unknown.",
        evidence=list(evidence.values()), missing_data=["Validated clinical rules and mission-specific context are not available."]))
    evaluated = [r.rule_id for r in results if r.outcome != "insufficient_data"]
    missing = [r.rule_id for r in results if r.outcome == "insufficient_data"]
    statuses = {r.workflow_status for r in results if r.outcome == "triggered"}
    status = "crew_medical_review" if "crew_medical_review" in statuses else "review_suggested" if statuses else "insufficient_data" if any(r.outcome == "insufficient_data" for r in results[:-1]) else "no_rule_triggered"
    payload = {"astronaut_id": astronaut_id, "evidence": [e.model_dump(mode="json") for e in sorted(evidence.values(), key=lambda e: e.indicator)],
        "checkin": checkin.model_dump(mode="json") if checkin else None}
    fingerprint = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return d.Assessment(id=assessment_id or str(uuid5(UUID(astronaut_id), RULESET_VERSION + fingerprint)), created_at=now, evaluated_at=now,
        astronaut_id=astronaut_id, ruleset_version=RULESET_VERSION, input_fingerprint=fingerprint, status=status,
        coverage=d.Coverage(evaluated_rule_ids=evaluated, insufficient_rule_ids=missing), results=results)


def assess_checkin(checkin: d.DailyCheckin, readings: list[d.HealthReading]) -> d.Assessment:
    return evaluate(checkin.astronaut_id, readings, [], checkin, checkin.created_at, assessment_id_for(checkin.id))
