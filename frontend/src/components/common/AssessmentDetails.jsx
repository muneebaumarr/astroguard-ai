import { Link } from 'react-router'

export const educationalDisclaimer = 'Fictional educational decision support only. No diagnosis, emergency prediction, clinical validation or safety clearance. Demo thresholds are not NASA-approved medical standards.'
export const humanize = value => value.replaceAll('_', ' ')

export function AssessmentDetails({ assessment }) {
  if (!assessment) return <p>No assessment available. Save a check-in, advance a simulation tick or evaluate stored observations.</p>
  return <div className="assessment-details"><div className="panel-heading"><h3>Assessment explanation</h3><span className={`review-badge ${assessment.status}`}>{humanize(assessment.status)}</span></div>
    <p className="sensor-time">Evaluated {assessment.evaluated_at} · {assessment.ruleset_version}</p>
    <ul className="rule-results">{assessment.results.map(result => <li key={result.rule_id}>
      <div className="rule-title"><strong>{humanize(result.rule_id)}</strong><span className={`review-badge ${result.workflow_status}`}>{humanize(result.outcome)}</span></div>
      <p>{result.explanation}</p>
      {result.evidence.length > 0 && <ul className="evidence-list" aria-label={`Evidence for ${result.rule_id}`}>{result.evidence.map(item => <li key={`${item.record_id}:${item.indicator}`}>
        <strong>{humanize(item.indicator)}: {item.value} {item.unit}</strong><span>{item.observed_at} · {humanize(item.record_type)}</span>
      </li>)}</ul>}
      {result.missing_data.length > 0 && <p className="field-help">Missing context: {result.missing_data.join(', ')}</p>}
    </li>)}</ul><p className="field-help">{educationalDisclaimer}</p></div>
}

export function RecentAlerts({ alerts = [], assessments = [], onAcknowledge, busy = false, compact = false }) {
  const visible = compact ? alerts.slice(0, 4) : alerts
  return <section className="panel alert-panel" aria-label="Recent alerts"><div className="panel-heading"><h2>Recent alerts</h2><Link to="/assessments">View assessments & alerts</Link></div>
    {!visible.length && <p>No alerts recorded. This does not establish medical safety.</p>}
    <ul className="alert-list">{visible.map(alert => {
      const assessment = assessments.find(item => item.id === alert.latest_assessment_id)
      const reason = assessment?.results.find(item => item.rule_id === alert.rule_id)
      return <li key={alert.id}><div className="rule-title"><strong>{humanize(alert.rule_id)}</strong><span className={`review-badge ${alert.workflow_status}`}>{humanize(alert.workflow_status)}</span></div>
        <p>{reason?.explanation || 'Open the linked assessment for the supporting observations.'}</p>
        <p className="sensor-time">Opened {alert.opened_at} · {humanize(alert.state)}</p>
        {alert.acknowledged_at && <p className="sensor-time">Acknowledged {alert.acknowledged_at}</p>}
        {alert.resolved_at && <p className="sensor-time">Resolved {alert.resolved_at} · demo rule no longer triggered</p>}
        <div className="simulator-actions"><Link to={`/assessments?assessment=${alert.latest_assessment_id}`}>Supporting assessment</Link>
          {onAcknowledge && alert.state === 'open' && <button className="text-button" disabled={busy} onClick={() => onAcknowledge(alert.id)}>Acknowledge alert</button>}</div>
      </li>
    })}</ul><p className="field-help">{educationalDisclaimer}</p></section>
}
