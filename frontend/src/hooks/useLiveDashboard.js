import { useEffect, useRef, useState } from 'react'
import { api } from '../services/api'

export function useLiveDashboard(astronautId, missionId) {
  const [view, setView] = useState({ status: 'loading', health: [], environment: [], scenarios: [], runs: [], run: null, active: null, checkins: [], assessments: [], alerts: [] })
  const [busy, setBusy] = useState(false)
  const [playing, setPlaying] = useState(false)
  const [error, setError] = useState('')
  const alive = useRef(false), pending = useRef(false), playback = useRef(false)
  const timer = useRef(null), controller = useRef(null), retry = useRef(null), state = useRef(view)

  function pause() {
    playback.current = false
    clearTimeout(timer.current)
    setPlaying(false)
  }

  async function load(signal) {
    const [health, environment, history, cabin, scenarios, runs, checkins, assessments, alerts] = await Promise.all([
      api.healthTelemetry(astronautId, signal), api.environmentalTelemetry(missionId, signal),
      api.healthHistory(astronautId, signal), api.environmentHistory(missionId, signal),
      api.simulationScenarios(signal), api.simulationRuns(signal), api.checkins(astronautId, signal), api.assessments(astronautId, signal),
      api.alerts(astronautId, signal),
    ])
    const own = runs.filter(run => run.astronaut_id === astronautId && run.mission_id === missionId)
      .sort((a, b) => b.created_at.localeCompare(a.created_at) || b.id.localeCompare(a.id))
    const run = own.find(run => ['paused', 'running'].includes(run.status)) || own[0] || null
    const result = { status: 'ready', health: health.readings, environment: environment.readings, history, cabin, scenarios, runs,
      run, active: runs.find(run => ['paused', 'running'].includes(run.status)) || null, alerts,
      checkins: [...checkins].sort((a, b) => b.observed_at.localeCompare(a.observed_at)),
      assessments: [...assessments].sort((a, b) => b.evaluated_at.localeCompare(a.evaluated_at)) }
    if (alive.current && !signal.aborted) { state.current = result; setView(result) }
  }

  useEffect(() => {
    alive.current = true
    const initial = new AbortController()
    load(initial.signal).catch(error => {
      if (alive.current && !initial.signal.aborted) { setError(error.message); setView(previous => ({ ...previous, status: 'error' })) }
    })
    return () => {
      alive.current = false; playback.current = false; clearTimeout(timer.current)
      initial.abort(); controller.current?.abort()
    }
    // The dashboard workspace is keyed by astronaut and mission; each selection owns its lifecycle.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [astronautId, missionId])

  async function refresh() {
    if (pending.current) return
    pause(); pending.current = true; setBusy(true)
    setError(retry.current ? 'Previous command outcome is unknown. Retry the same command before continuing.' : '')
    controller.current = new AbortController()
    try { await load(controller.current.signal) }
    catch (error) { if (alive.current && error.name !== 'AbortError') setError(error.message) }
    finally { pending.current = false; if (alive.current) setBusy(false) }
  }

  async function command(action, id, body) {
    if (pending.current || !alive.current) return false
    pending.current = true; setBusy(true); setError('')
    const signature = JSON.stringify([action, id, body])
    if (!retry.current || retry.current.signature !== signature) retry.current = { action, id, body, signature, key: crypto.randomUUID() }
    const work = retry.current
    controller.current = new AbortController()
    try {
      await api.simulationCommand(work.action, work.id, work.body, work.key, controller.current.signal)
      if (!alive.current) return false
      retry.current = null // Acknowledged mutations must never be repeated to repair a GET failure.
      await load(controller.current.signal)
      return alive.current
    } catch (error) {
      if (alive.current && error.name !== 'AbortError') { pause(); setError(`${error.message} Playback stopped. Retry the same command if its result is unknown, or refresh saved state.`) }
      return false
    } finally { pending.current = false; if (alive.current) setBusy(false) }
  }

  async function tick() {
    const run = state.current.run
    if (!run || pending.current) return false
    if (run.status === 'running' && !await command('pause', run.id, null)) return false
    return command('steps', run.id, { steps: 1 })
  }

  function schedule() {
    clearTimeout(timer.current)
    timer.current = setTimeout(async () => {
      if (!playback.current || !alive.current) return
      const success = await tick()
      if (success && playback.current && alive.current) schedule()
    }, 2000)
  }

  function play() {
    if (playback.current || pending.current || !['paused', 'running'].includes(state.current.run?.status) || retry.current) return
    playback.current = true; setPlaying(true); schedule()
  }

  function start(scenario) {
    pause()
    // Preserve the exact timestamp/payload when a lost create response is retried.
    const body = retry.current?.action === 'create' && retry.current.body.scenario === scenario ? retry.current.body : {
      astronaut_id: astronautId, scenario, seed: 42, simulation_start_at: new Date().toISOString(), interval_seconds: 2, step_seconds: 60,
    }
    return command('create', null, body)
  }

  return { ...view, busy, playing, error, refresh, play, pause, start,
    step: () => { pause(); return tick() },
    stop: () => { pause(); return command('stop', state.current.run.id, null) },
    retryCommand: retry.current ? () => { const work = retry.current; return command(work.action, work.id, work.body) } : null }
}
