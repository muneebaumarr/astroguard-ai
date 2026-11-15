// Reading suggestions, never diagnoses or hazard inference. No threshold engine lives here.
const byIndicator = { spo2: 'environmental_monitoring', cabin_co2: 'environmental_monitoring', radiation_dose_rate: 'radiation_awareness',
  sleep_hours: 'sleep_circadian', stress: 'crew_wellbeing', mood: 'crew_wellbeing', exercise_minutes: 'exercise_conditioning' }

export function guidanceSuggestions({ astronautId, articles, assessments = [], alerts = [], checkins = [], readings = [] }) {
  const result = new Map(), available = new Set(articles.map(article => article.slug))
  function add(slug, reason) {
    if (!available.has(slug)) return
    if (!result.has(slug)) result.set(slug, { slug, reasons: [] })
    if (!result.get(slug).reasons.includes(reason)) result.get(slug).reasons.push(reason)
  }
  const ownAssessments = assessments.filter(item => item.astronaut_id === astronautId)
    .sort((a, b) => b.evaluated_at.localeCompare(a.evaluated_at))
  const latest = ownAssessments[0]
  const relevant = new Set(latest ? [latest.id] : [])
  for (const alert of alerts.filter(item => item.astronaut_id === astronautId && item.state !== 'resolved')) relevant.add(alert.latest_assessment_id)
  for (const assessment of ownAssessments.filter(item => relevant.has(item.id))) {
    for (const rule of assessment.results.filter(rule => rule.outcome === 'triggered')) {
      for (const evidence of rule.evidence) {
        const slug = byIndicator[evidence.indicator]
        if (slug) add(slug, `Fictional assessment considered ${evidence.indicator.replaceAll('_', ' ')}: ${evidence.value} ${evidence.unit} at ${evidence.observed_at}. This suggests a reading topic, not a cause or intervention.`)
      }
      for (const slug of rule.guidance_slugs || []) add(slug, `The fictional assessment links rule ${rule.rule_id} to this educational topic; the link is not a validated intervention.`)
    }
  }
  const checkin = checkins.filter(item => item.astronaut_id === astronautId).sort((a, b) => b.observed_at.localeCompare(a.observed_at))[0]
  if (checkin) {
    for (const [field, unit] of [['sleep_hours', 'h'], ['stress', 'scale_1_5'], ['mood', 'scale_1_5'], ['exercise_minutes', 'min']]) {
      if (checkin[field] != null) add(byIndicator[field], `Fictional check-in recorded ${field.replaceAll('_', ' ')}: ${checkin[field]} ${unit} at ${checkin.observed_at}. Presence of this entry offers context, not a health conclusion.`)
    }
  }
  for (const reading of readings.filter(item => item.astronaut_id === astronautId)) {
    if (byIndicator[reading.indicator]) add(byIndicator[reading.indicator], `Selected astronaut telemetry records ${reading.indicator}: ${reading.value} ${reading.unit} at ${reading.observed_at}. This is a simulated observation, not proof of a hazard.`)
  }
  return [...result.values()]
}
