import { useEffect, useRef, useState } from 'react'
import { useOutletContext } from 'react-router'
import { Activity, Play, SkipForward, Square, RefreshCw } from 'lucide-react'
import { PageHeading } from '../components/common/PageHeading'
import { ProfileGate } from '../components/common/ProfileGate'
import { LoadingState } from '../components/common/States'
import { api } from '../services/api'

function latest(readings) {
  const result = new Map()
  for (const reading of [...readings].sort((a, b) => a.tick_index - b.tick_index || a.id.localeCompare(b.id))) result.set(reading.indicator, reading)
  return [...result.values()]
}

const sensors = [
  ['heart_rate', 'Heart rate', 'bpm', 'health'], ['spo2', 'Oxygen saturation', '%', 'health'],
  ['body_temperature', 'Body temperature', 'degC', 'health'],
  ['cabin_co2', 'Cabin CO₂', 'ppm', 'environment'], ['radiation_dose_rate', 'Cabin radiation dose rate', 'uSv/h', 'environment'],
]

export function MissionSimulator() {
  const data = useOutletContext()
  return <><PageHeading title="Mission simulator">Fictional sensor telemetry, one deliberate tick at a time.</PageHeading>
    <ProfileGate data={data}>{data.profile.status === 'ready' && <SimulatorWorkspace key={data.selectedId}
      astronaut={data.profile.astronaut} mission={data.profile.mission} crew={data.astronauts} />}</ProfileGate></>
}

function SimulatorWorkspace({ astronaut, mission, crew }) {
  const [view, setView] = useState({ status: 'loading', runs: [], scenarios: [], run: null, health: [], environment: [], active: null })
  const [generation, setGeneration] = useState(0)
  const [form, setForm] = useState({ scenario: 'routine', seed: '42', start: new Date().toISOString().slice(0, 19) })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const pending = useRef(false)
  const retryCommand = useRef(null)
  const mounted = useRef(false)
  const controller = useRef(null)
  const selection = useRef('')
  const storageKey = `astroguard.simulation.${astronaut.id}`

  useEffect(() => {
    mounted.current = true
    try { selection.current = sessionStorage.getItem(storageKey) || '' } catch { /* Optional selection persistence. */ }
    return () => { mounted.current = false; controller.current?.abort() }
  }, [storageKey])

  useEffect(() => {
    let current = true
    const readController = new AbortController()
    setView(previous => ({ ...previous, status: 'loading' }))
    async function load() {
      try {
        const [scenarios, allRuns] = await Promise.all([api.simulationScenarios(readController.signal), api.simulationRuns(readController.signal)])
        const runs = allRuns.filter(run => run.astronaut_id === astronaut.id && run.mission_id === mission.id)
          .sort((a, b) => b.created_at.localeCompare(a.created_at) || b.id.localeCompare(a.id))
        const active = allRuns.find(run => ['paused', 'running'].includes(run.status)) || null
        const chosen = runs.find(run => run.id === selection.current) || runs.find(run => ['paused', 'running'].includes(run.status)) || runs[0] || null
        const run = chosen ? await api.simulationRun(chosen.id, readController.signal) : null
        const [health, environment] = run ? await Promise.all([
          api.runHealth(astronaut.id, run.id, readController.signal), api.runEnvironment(mission.id, run.id, readController.signal),
        ]) : [[], []]
        if (current) setView({ status: 'ready', scenarios, runs, run, active, health: latest(health), environment: latest(environment) })
      } catch (error) {
        if (current && error.name !== 'AbortError') setView({ status: 'error', scenarios: [], runs: [], run: null, active: null, health: [], environment: [], error: error.message })
      }
    }
    load()
    return () => { current = false; readController.abort() }
  }, [astronaut.id, mission.id, generation])

  function remember(id) {
    selection.current = id
    try { sessionStorage.setItem(storageKey, id) } catch { /* Backend is authoritative. */ }
  }

  async function command(action, id, body) {
    if (pending.current) return
    const signature = JSON.stringify([action, id, body])
    if (!retryCommand.current || retryCommand.current.signature !== signature) retryCommand.current = { signature, key: crypto.randomUUID(), action, id, body }
    const work = retryCommand.current
    pending.current = true
    setBusy(true)
    setError('')
    setSuccess('')
    controller.current = new AbortController()
    try {
      const result = await api.simulationCommand(work.action, work.id, work.body, work.key, controller.current.signal)
      if (!mounted.current) return
      remember((result.run || result).id)
      retryCommand.current = null
      setSuccess(action === 'create' ? 'Simulation created. Advance a tick to generate fictional readings.' : action === 'steps' ? 'One fictional tick saved successfully.' : `Run ${action === 'stop' ? 'stopped' : 'paused'}.`)
      setGeneration(value => value + 1)
    } catch (error) {
      if (mounted.current && error.name !== 'AbortError') setError(error.message)
    } finally {
      pending.current = false
      if (mounted.current) setBusy(false)
    }
  }

  function start(event) {
    event.preventDefault()
    if (!Number.isSafeInteger(Number(form.seed)) || form.seed.trim() === '' || !form.start || Number.isNaN(Date.parse(`${form.start}Z`))) {
      setError('Enter an integer seed and a valid UTC start time.')
      return
    }
    command('create', null, { astronaut_id: astronaut.id, scenario: form.scenario, seed: Number(form.seed), simulation_start_at: `${form.start}Z`, interval_seconds: 5, step_seconds: 60 })
  }

  const run = view.run
  const blocked = view.active && view.active.id !== run?.id
  const ready = view.status === 'ready' && !busy
  const description = view.scenarios.find(value => value.scenario === form.scenario)?.description
  return <div className="simulator">
    <section className="panel simulator-context"><div><span className="eyebrow cyan">SIMULATED · FICTIONAL</span><h2>{astronaut.display_name}</h2><p>{mission.name} · {mission.environment}</p></div><Activity size={28} /></section>
    <div className="notice"><p>Explicit ticks only. These authored values are not real sensor readings or medical assessments. Cabin radiation rate is not personal dosimetry.</p></div>
    {view.status === 'loading' && <LoadingState>Loading simulation state…</LoadingState>}
    {view.status === 'error' && <div className="history-error panel" role="alert"><p>{view.error}</p><button className="button" onClick={() => setGeneration(value => value + 1)}>Retry simulation load</button></div>}
    {error && <div className="history-error panel" role="alert"><p>{error}</p>{retryCommand.current && <button className="button" disabled={busy} onClick={() => {
      const work = retryCommand.current; command(work.action, work.id, work.body)
    }}>Retry same command</button>}</div>}
    {success && <p className="save-confirmation" role="status">{success}</p>}
    {blocked && <p className="notice">An active run belongs to {crew.find(person => person.id === view.active.astronaut_id)?.display_name || 'another crew profile'}. Select that profile and stop its run before starting another.</p>}
    <div className="simulator-columns"><form className="panel simulator-controls" onSubmit={start} aria-label="Simulation configuration">
      <h2>Start a fictional run</h2><fieldset disabled={!ready || Boolean(view.active)}>
        <div className="form-field"><label htmlFor="sim-scenario">Scenario</label><select id="sim-scenario" value={form.scenario} onChange={event => setForm({ ...form, scenario: event.target.value })}>
          {view.scenarios.map(item => <option key={item.scenario} value={item.scenario}>{item.scenario.replaceAll('_', ' ')}</option>)}</select><p className="field-help">{description}</p></div>
        <div className="form-field"><label htmlFor="sim-seed">Deterministic seed</label><input id="sim-seed" type="number" step="1" value={form.seed} onChange={event => setForm({ ...form, seed: event.target.value })} /></div>
        <div className="form-field"><label htmlFor="sim-start">Simulation start (UTC)</label><input id="sim-start" type="datetime-local" step="1" value={form.start} onChange={event => setForm({ ...form, start: event.target.value })} /></div>
        <p className="field-help">Each explicit tick advances simulated time by 60 seconds. No automatic timer runs.</p>
        <button className="button" type="submit"><Play size={15} />Start simulation</button>
      </fieldset>{view.active && !blocked && <p className="field-help">Stop the existing run before starting a new scenario. A seeded demo run may already be present.</p>}
    </form>
    <section className="panel simulator-controls" aria-label="Simulation status"><h2>Run status</h2>
      {view.runs.length > 0 && <div className="form-field"><label htmlFor="sim-run">Saved runs for this astronaut</label><select id="sim-run" value={run?.id || ''} disabled={!ready} onChange={event => { remember(event.target.value); setGeneration(value => value + 1) }}>
        {view.runs.map(item => <option value={item.id} key={item.id}>{item.scenario.replaceAll('_', ' ')} · {item.status} · {item.created_at}</option>)}</select></div>}
      <dl className="run-facts"><div><dt>Status</dt><dd>{run?.status || 'No run yet'}</dd></div><div><dt>Scenario</dt><dd>{run?.scenario.replaceAll('_', ' ') || 'Not selected'}</dd></div>
        <div><dt>Last tick index</dt><dd>{run ? run.last_tick_index < 0 ? 'No ticks yet' : run.last_tick_index : 'No data'}</dd></div><div><dt>Seed</dt><dd>{run?.seed ?? 'No data'}</dd></div></dl>
      <div className="simulator-actions"><button className="button" disabled={!ready || run?.status !== 'paused'} onClick={() => command('steps', run.id, { steps: 1 })}><SkipForward size={15} />Advance one tick</button>
        {run?.status === 'running' && <button className="button" disabled={!ready} onClick={() => command('pause', run.id, null)}>Pause to step</button>}
        <button className="button" disabled={!ready || !['paused', 'running'].includes(run?.status)} onClick={() => command('stop', run.id, null)}><Square size={14} />Stop run</button>
        <button className="text-button" disabled={busy} onClick={() => setGeneration(value => value + 1)}><RefreshCw size={14} />Refresh saved state</button></div>
      <p className="field-help">Refresh reads stored records. Backend restarts clear memory.</p>
    </section></div>
    <div className="section-heading"><h2>Latest fictional health telemetry</h2><span>Selected run only</span></div>
    <div className="metrics-grid">{sensors.filter(value => value[3] === 'health').map(sensor => <SensorCard key={sensor[0]} sensor={sensor} readings={view.health} />)}</div>
    <div className="section-heading"><h2>Mission cabin environment</h2><span>Separate from astronaut health</span></div>
    <div className="metrics-grid">{sensors.filter(value => value[3] === 'environment').map(sensor => <SensorCard key={sensor[0]} sensor={sensor} readings={view.environment} />)}</div>
  </div>
}

function SensorCard({ sensor: [indicator, label, unit], readings }) {
  const reading = readings.find(value => value.indicator === indicator)
  return <article className="panel metric-card"><div className="metric-top">{label}</div><div className="metric-value">{reading?.value ?? 'No data'}<span>{unit}</span></div>
    <p className="field-help">Simulated · Fictional</p><p className="sensor-time">{reading ? reading.observed_at.replace('T', ' ').replace('Z', ' UTC') : 'Awaiting an explicit tick'}</p></article>
}
