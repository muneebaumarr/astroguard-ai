import { useEffect, useRef, useState } from 'react'
import { useOutletContext } from 'react-router'
import { CheckCircle2, ClipboardPlus, History } from 'lucide-react'
import { PageHeading } from '../components/common/PageHeading'
import { ProfileGate } from '../components/common/ProfileGate'
import { EmptyState, LoadingState } from '../components/common/States'
import { SavedCheckin } from '../components/checkins/SavedCheckin'
import { useCheckinHistory } from '../hooks/useCheckinHistory'
import { api } from '../services/api'
import { initialForm, validateCheckin, validationErrors, vitalFields } from '../services/checkinForm'

export function DailyCheckin() {
  const data = useOutletContext()
  return <><PageHeading title="Daily check-in">Record what you know. Keep the rest unknown.</PageHeading>
    <ProfileGate data={data}>
      {data.profile.status === 'ready' && <CheckinWorkspace key={data.selectedId} astronaut={data.profile.astronaut} mission={data.profile.mission} />}
    </ProfileGate></>
}

function CheckinWorkspace({ astronaut, mission }) {
  const history = useCheckinHistory(astronaut.id)
  const [form, setForm] = useState(initialForm)
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [success, setSuccess] = useState(false)
  const [saved, setSaved] = useState(null)
  const [detailState, setDetailState] = useState({ loading: false, error: null })
  const pending = useRef(false)
  const command = useRef(null)
  const mounted = useRef(false)
  const writeController = useRef(null)
  const detailController = useRef(null)
  const detailVersion = useRef(0)
  const rememberedId = useRef(null)
  const storageKey = `astroguard.selectedCheckin.${astronaut.id}`
  if (rememberedId.current === null) {
    try { rememberedId.current = sessionStorage.getItem(storageKey) || '' } catch { rememberedId.current = '' }
  }

  function rememberCheckin(id) {
    rememberedId.current = id
    try { sessionStorage.setItem(storageKey, id) } catch { /* Backend history remains authoritative. */ }
  }

  function assessmentFor(checkin) {
    return history.assessments.find(item => item.results.some(result => result.evidence.some(value => value.record_id === checkin.id))) || null
  }

  // A reload loses the POST response in React state, not the committed record.
  // Restore from the freshly fetched history; store only a per-astronaut ID in
  // sessionStorage, never a second copy of health data. Stale IDs fall back safely.
  const restored = history.status === 'ready'
    ? history.checkins.find(item => item.id === rememberedId.current) || history.checkins[0] : null
  const displayed = detailState.loading || detailState.error ? null
    : saved || (restored ? { checkin: restored, assessment: assessmentFor(restored) } : null)

  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false; writeController.current?.abort(); detailController.current?.abort() }
  }, [])

  function change(event) {
    const { name, value } = event.target
    setForm(previous => ({ ...previous, [name]: value }))
    setErrors(previous => ({ ...previous, [name]: undefined, form: undefined }))
  }

  async function submit(event) {
    event.preventDefault()
    if (pending.current || success) return
    const { body, errors: invalid } = validateCheckin(form)
    setErrors(invalid)
    if (Object.keys(invalid).length) return
    const signature = JSON.stringify(body)
    if (!command.current || command.current.signature !== signature) {
      command.current = { signature, body, key: crypto.randomUUID() }
    }
    pending.current = true
    setBusy(true)
    const controller = new AbortController()
    writeController.current = controller
    try {
      const result = await api.createCheckin(astronaut.id, command.current.body, command.current.key, controller.signal)
      if (!mounted.current) return
      detailController.current?.abort()
      detailVersion.current += 1
      setDetailState({ loading: false, error: null })
      setSaved({ checkin: result.checkin, assessment: result.assessment })
      rememberCheckin(result.checkin.id)
      setSuccess(true)
      history.refresh()
    } catch (error) {
      if (mounted.current && error.name !== 'AbortError') setErrors(validationErrors(error, body))
    } finally {
      pending.current = false
      if (mounted.current) setBusy(false)
    }
  }

  async function selectCheckin(id) {
    detailController.current?.abort()
    const controller = new AbortController()
    detailController.current = controller
    const version = ++detailVersion.current
    setDetailState({ loading: true, error: null })
    setSaved(null)
    try {
      const checkin = await api.checkin(astronaut.id, id, controller.signal)
      const assessment = assessmentFor(checkin)
      if (mounted.current && version === detailVersion.current) {
        setSaved({ checkin, assessment })
        rememberCheckin(checkin.id)
        setDetailState({ loading: false, error: null })
      }
    } catch (error) {
      if (mounted.current && version === detailVersion.current && error.name !== 'AbortError') setDetailState({ loading: false, error: error.message })
    }
  }

  function newEntry() {
    command.current = null
    setSuccess(false)
    setForm(initialForm())
    setErrors({})
  }

  function field(name, label, { unit, type = 'number', min, max, step = 'any', required = false } = {}) {
    return <div className="form-field" key={name}><label htmlFor={`checkin-${name}`}>{label}{unit && <span className="field-unit">{unit}</span>}<small>{required ? 'Required' : 'Optional'}</small></label>
      <input id={`checkin-${name}`} name={name} type={type} value={form[name]} onChange={change}
        min={min} max={max} step={type === 'number' ? step : undefined} required={required}
        aria-invalid={Boolean(errors[name])} aria-describedby={errors[name] ? `error-${name}` : undefined} />
      {errors[name] && <p id={`error-${name}`} className="field-error">{errors[name]}</p>}
    </div>
  }

  return <div className="checkin-workspace">
    <div className="checkin-profile panel"><div><span className="eyebrow cyan">FICTIONAL CREW PROFILE</span><h2>{astronaut.display_name}</h2><p>{mission.name} · {mission.environment.replaceAll('_', ' ')}</p></div>
      <span className="outline-label"><ClipboardPlus size={15} />Manual observations</span></div>
    <div className="notice"><p>All health fields are optional. Supply at least one observation. Dates and times use UTC. Entries stay available while this backend process is running.</p></div>
    {success && <div className="save-confirmation" role="status"><CheckCircle2 size={21} /><div><strong>Check-in saved successfully</strong><p>Your fictional observations and educational assessment were saved together.</p></div><button className="button" onClick={newEntry}>Start another entry</button></div>}
    {displayed && <SavedCheckin {...displayed} />}
    <div className="checkin-columns"><form className="panel checkin-form" onSubmit={submit} noValidate aria-label="Daily health check-in">
      <fieldset disabled={busy || success}><legend>Observation details</legend><div className="form-grid">
        {field('checkin_date', 'Check-in date (UTC)', { type: 'date', required: true })}
        {field('observation_time', 'Observation time (UTC)', { type: 'time', required: true })}
        <div className="form-field"><label htmlFor="checkin-context">Observation context<small>Required</small></label><select id="checkin-context" name="context" value={form.context} onChange={change}>
          <option value="resting">Resting</option><option value="exercise">Exercise</option><option value="recovery">Recovery</option><option value="unspecified">Unspecified</option>
        </select>{errors.context && <p className="field-error">{errors.context}</p>}</div>
      </div></fieldset>
      <fieldset disabled={busy || success}><legend>Vital signs</legend><p className="section-help">Enter measurements you actually recorded. Blood pressure needs both components.</p>
        <div className="form-grid">{vitalFields.map(({ key, label, ...settings }) => field(key, label, settings))}</div></fieldset>
      <fieldset disabled={busy || success}><legend>Sleep & wellness</legend><div className="form-grid">
        {field('sleep_hours', 'Sleep duration', { unit: 'h', min: 0, max: 24 })}
        {['mood', 'stress'].map(name => <div className="form-field" key={name}><label htmlFor={`checkin-${name}`}>{name === 'mood' ? 'Mood' : 'Stress'}<small>Optional</small></label>
          <select id={`checkin-${name}`} name={name} value={form[name]} onChange={change}><option value="">Not recorded</option>
            {[1, 2, 3, 4, 5].map(value => <option key={value} value={value}>{value} / 5</option>)}</select>
          <p className="field-help">Higher means {name === 'mood' ? 'more positive mood' : 'more stress'}.</p>
          {errors[name] && <p className="field-error">{errors[name]}</p>}</div>)}
      </div></fieldset>
      <fieldset disabled={busy || success}><legend>Activity</legend><div className="form-grid">{field('exercise_minutes', 'Exercise activity', { unit: 'min', min: 0, max: 1440, step: '1' })}</div></fieldset>
      <fieldset disabled={busy || success}><legend>Symptoms & notes</legend>
        <div className="form-field"><label htmlFor="checkin-symptoms">Symptoms<small>Optional</small></label>
          <textarea id="checkin-symptoms" name="symptoms" rows={3} value={form.symptoms} onChange={change} aria-invalid={Boolean(errors.symptoms)} />
          <p className="field-help">One per line. Up to 20 entries, 100 characters each.</p>{errors.symptoms && <p className="field-error">{errors.symptoms}</p>}</div>
        <div className="form-field"><label htmlFor="checkin-notes">Additional notes<small>Optional</small></label>
          <textarea id="checkin-notes" name="notes" rows={3} maxLength={2000} value={form.notes} onChange={change} />
          {errors.notes && <p className="field-error">{errors.notes}</p>}</div>
      </fieldset>
      <div className="form-actions">{errors.form && <p className="field-error" role="alert">{errors.form}</p>}
        <p className="field-help">Fictional educational demo. No clinical diagnosis or treatment advice.</p>
        <button className="button" type="submit" disabled={busy || success}>{busy ? 'Saving check-in…' : success ? 'Saved' : command.current ? 'Retry / save check-in' : 'Save check-in'}</button>
      </div>
    </form>
    <aside className="panel checkin-history" aria-label="Previous check-ins"><div className="panel-heading"><h2><History size={18} />Previous check-ins</h2><button className="text-button" onClick={history.refresh}>Refresh</button></div>
      {history.status === 'loading' && <LoadingState>Loading previous check-ins…</LoadingState>}
      {history.status === 'error' && <div className="history-error" role="alert"><p>{history.error}</p><button className="button" onClick={history.refresh}>Retry history</button></div>}
      {history.status === 'ready' && !history.checkins.length && <EmptyState title="No check-ins yet">Your saved observations will appear here.</EmptyState>}
      {history.status === 'ready' && history.checkins.length > 0 && <ul className="checkin-list">{history.checkins.map(checkin => <li key={checkin.id}>
        <button onClick={() => selectCheckin(checkin.id)} aria-pressed={displayed?.checkin.id === checkin.id}><strong>{checkin.checkin_date}</strong><span>{checkin.context} · Manual · Fictional</span><small>View saved observations →</small></button>
      </li>)}</ul>}
    </aside></div>
    {detailState.loading && <LoadingState>Loading saved observations…</LoadingState>}
    {detailState.error && <p className="field-error" role="alert">{detailState.error}</p>}
  </div>
}
