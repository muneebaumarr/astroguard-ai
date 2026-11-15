import { useEffect, useRef, useState } from 'react'
import { useOutletContext, useSearchParams } from 'react-router'
import { PageHeading } from '../components/common/PageHeading'
import { ProfileGate } from '../components/common/ProfileGate'
import { AssessmentDetails, RecentAlerts, educationalDisclaimer, humanize } from '../components/common/AssessmentDetails'
import { api } from '../services/api'

export function Assessments() {
  const data = useOutletContext()
  return <><PageHeading title="Assessments & alerts">Evidence-led fictional review, with every demonstration rule explained.</PageHeading>
    <ProfileGate data={data}>{data.profile.status === 'ready' && <AssessmentWorkspace key={data.selectedId} astronaut={data.profile.astronaut} />}</ProfileGate></>
}

function AssessmentWorkspace({ astronaut }) {
  const [view, setView] = useState({ status: 'loading', assessments: [], alerts: [] })
  const [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const [params, setParams] = useSearchParams()
  const mounted = useRef(false), pending = useRef(false), retry = useRef(null), controller = useRef(null)
  async function load(signal) {
    const [assessments, alerts] = await Promise.all([api.assessments(astronaut.id, signal), api.alerts(astronaut.id, signal)])
    if (mounted.current && !signal.aborted) setView({ status: 'ready', assessments, alerts })
  }
  useEffect(() => {
    mounted.current = true
    controller.current = new AbortController()
    const initial = controller.current
    load(initial.signal).catch(error => { if (mounted.current && !initial.signal.aborted) { setError(error.message); setView(previous => ({ ...previous, status: 'error' })) } })
    return () => { mounted.current = false; controller.current?.abort() }
  }, [astronaut.id])

  async function action(operation = 'refresh', alertId = null) {
    if (pending.current) return
    pending.current = true; setBusy(true); setError('')
    controller.current = new AbortController()
    try {
      if (operation !== 'refresh') {
        const signature = `${operation}:${alertId}`
        if (retry.current?.signature !== signature) retry.current = { signature, operation, alertId, key: crypto.randomUUID() }
        const result = await api.assessmentCommand(astronaut.id, operation, alertId, retry.current.key, controller.current.signal)
        if (!mounted.current) return
        retry.current = null
        if (operation === 'evaluate') setParams({ assessment: result.id })
      }
      await load(controller.current.signal)
      if (retry.current && mounted.current) setError('A previous command result is unknown. Retry the same command to confirm it.')
    } catch (error) { if (mounted.current && error.name !== 'AbortError') setError(error.message) }
    finally { pending.current = false; if (mounted.current) setBusy(false) }
  }

  const selectedId = params.get('assessment')
  const selected = selectedId ? view.assessments.find(item => item.id === selectedId) : view.assessments[0]
  return <div className="assessment-workspace"><section className="panel assessment-toolbar"><div><span className="eyebrow cyan">FICTIONAL EDUCATIONAL REVIEW</span><h2>{astronaut.display_name}</h2><p>{educationalDisclaimer}</p></div>
    <div className="simulator-actions"><button className="button" disabled={busy || view.status === 'loading'} onClick={() => action('evaluate')}>Evaluate stored observations</button><button className="text-button" disabled={busy || view.status === 'loading'} onClick={() => action()}>Refresh assessments</button></div></section>
    {view.status === 'loading' && <p role="status">Loading assessments and alerts…</p>}
    {error && <div className="history-error panel" role="alert"><p>{error}</p>{retry.current && <button className="button" disabled={busy} onClick={() => action(retry.current.operation, retry.current.alertId)}>Retry same command</button>}</div>}
    <div className="assessment-columns"><section className="panel assessment-main"><h2>{selectedId ? 'Selected assessment' : 'Latest assessment'}</h2>
      {selectedId && !selected && view.status === 'ready' ? <p>This assessment is unavailable for the selected astronaut. <button className="text-button" onClick={() => setParams({})}>Show latest assessment</button></p> : <AssessmentDetails assessment={selected} />}
    </section><aside className="panel assessment-history"><h2>Assessment history</h2><ul>{view.assessments.map(item => <li key={item.id}><button className="text-button" aria-pressed={item.id === selected?.id} onClick={() => setParams({ assessment: item.id })}>{humanize(item.status)}<small>{item.evaluated_at}</small></button></li>)}</ul>{!view.assessments.length && <p>No assessments recorded.</p>}</aside></div>
    <RecentAlerts alerts={view.alerts} assessments={view.assessments} onAcknowledge={id => action('acknowledge', id)} busy={busy} />
  </div>
}
