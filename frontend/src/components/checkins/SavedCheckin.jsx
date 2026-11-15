import { vitalFields } from '../../services/checkinForm'

export function SavedCheckin({ checkin, assessment }) {
  const values = [
    ...checkin.readings.map(reading => ({ label: vitalFields.find(field => field.key === reading.indicator)?.label || reading.indicator, value: reading.value, unit: reading.unit })),
    ...[['sleep_hours', 'Sleep duration', 'h'], ['mood', 'Mood (higher is more positive)', '/ 5'],
      ['stress', 'Stress (higher is more stress)', '/ 5'], ['exercise_minutes', 'Exercise activity', 'min']]
      .filter(([key]) => checkin[key] !== null && checkin[key] !== undefined)
      .map(([key, label, unit]) => ({ label, value: checkin[key], unit })),
  ]
  return <section className="panel saved-checkin" aria-label="Saved check-in details">
    <div className="panel-heading"><h2>Saved check-in · {checkin.checkin_date}</h2><span className="outline-label">Manual · Fictional</span></div>
    <div className="saved-body"><p>Observed at {checkin.observed_at.replace('T', ' ').replace('Z', ' UTC')} · {checkin.context}</p>
      <dl className="saved-values">{values.map(({ label, value, unit }) => <div key={label}><dt>{label}</dt><dd>{value} <span>{unit}</span></dd></div>)}</dl>
      {checkin.symptoms.length > 0 && <div><h3>Reported symptoms</h3><ul>{checkin.symptoms.map((symptom, index) => <li key={index}>{symptom}</li>)}</ul></div>}
      {checkin.notes && <div><h3>Notes</h3><p className="preserve-whitespace">{checkin.notes}</p></div>}
      <div className="educational-assessment"><h3>Educational assessment</h3>
        {assessment ? <><strong>{assessment.status === 'review_suggested' ? 'Review suggested' : 'Insufficient information'}</strong>
          {assessment.results.map(result => <p key={result.rule_id}>{result.explanation}</p>)}
          <p className="assessment-limit">A demonstration of input review, not a diagnosis, severity rating or clinical readiness assessment.</p></>
          : <p>No educational assessment is linked to this check-in.</p>}
      </div>
    </div>
  </section>
}
