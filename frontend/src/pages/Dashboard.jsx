import { useState } from 'react'
import { useOutletContext, Link } from 'react-router'
import { Activity, Heart, Thermometer, Wind, Radio, Play, Pause, SkipForward, RefreshCw } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { PageHeading } from '../components/common/PageHeading'
import { ProfileGate } from '../components/common/ProfileGate'
import { useLiveDashboard } from '../hooks/useLiveDashboard'
import { RecentAlerts } from '../components/common/AssessmentDetails'

const sensors = [
  { indicator: 'heart_rate', label: 'Heart rate', unit: 'bpm', icon: Heart, color: '#38d9eb', domain: [50, 120] },
  { indicator: 'spo2', label: 'Oxygen saturation', unit: '%', icon: Wind, color: '#719bff', domain: [90, 100] },
  { indicator: 'body_temperature', label: 'Body temperature', unit: '°C', icon: Thermometer, color: '#c4a3ff', domain: [35, 39] },
  { indicator: 'cabin_co2', label: 'Cabin CO₂', unit: 'ppm', icon: Wind, color: '#49d8ad', domain: [0, 'auto'], environment: true },
  { indicator: 'radiation_dose_rate', label: 'Radiation dose rate', unit: 'uSv/h', icon: Radio, color: '#f6c66e', domain: [0, 'auto'], environment: true },
]
const time = value => new Date(value).toLocaleTimeString('en-GB', { timeZone: 'UTC', hour12: false })
const ordered = values => [...values].sort((a, b) => a.observed_at.localeCompare(b.observed_at) || a.id.localeCompare(b.id))

export function Dashboard() {
  const data = useOutletContext()
  return <><PageHeading title="Crew health overview" aside={<Link className="outline-label" to="/demo"><Radio size={14} />Open Mission Simulator</Link>}>
    Mission control · fictional astronaut telemetry and educational context.
  </PageHeading><ProfileGate data={data}>{data.profile.status === 'ready' && <MissionControl
    key={`${data.profile.astronaut.id}:${data.profile.mission.id}`} astronaut={data.profile.astronaut} mission={data.profile.mission} crew={data.astronauts} />}</ProfileGate></>
}

function MissionControl({ astronaut, mission, crew }) {
  const live = useLiveDashboard(astronaut.id, mission.id)
  const [scenario, setScenario] = useState('routine')
  const ready = live.status === 'ready' && !live.busy
  const usable = ['paused', 'running'].includes(live.run?.status)
  const blocked = live.active && live.active.astronaut_id !== astronaut.id
  const selectedHealth = (live.history || []).filter(value => value.simulation_run_id === live.run?.id)
  const selectedEnvironment = (live.cabin || []).filter(value => value.simulation_run_id === live.run?.id)
  const health = ordered(selectedHealth.length ? selectedHealth : live.history || [])
  const environment = ordered(selectedEnvironment.length ? selectedEnvironment : live.cabin || [])
  const checkin = live.checkins[0], assessment = live.assessments[0]
  return <div className="mission-control">
    <section className="panel control-header" aria-label="Selected astronaut">
      <div><span className="eyebrow cyan">SIMULATED DATA · FICTIONAL CREW</span><h2>Welcome aboard, <span>{astronaut.display_name}.</span></h2><p>{astronaut.role} · {mission.name} · {mission.environment.replaceAll('_', ' ')}</p></div>
      <div className={`playback-badge ${live.playing ? 'is-playing' : ''}`}><span />{live.playing ? 'Playback playing' : 'Playback paused'}<small>Backend run: {live.run?.status || 'not initialized'}</small></div>
    </section>
    <section className="panel overview-controls" aria-label="Overview simulation controls">
      <div className="form-field"><label htmlFor="overview-scenario">Scenario</label><select id="overview-scenario" value={scenario} disabled={!ready || live.playing || Boolean(live.active)} onChange={event => setScenario(event.target.value)}>{live.scenarios.map(item => <option key={item.scenario} value={item.scenario}>{item.scenario.replaceAll('_', ' ')}</option>)}</select></div>
      <div className="simulator-actions">
        <button className="button" disabled={!ready || Boolean(live.active) || live.playing} onClick={() => live.start(scenario)}>Start simulation</button>
        <button className="button" disabled={!ready || !usable || live.playing || Boolean(live.retryCommand)} onClick={live.play}><Play size={15} />Play</button>
        <button className="button" disabled={!live.playing} onClick={live.pause}><Pause size={15} />Pause</button>
        <button className="button" disabled={!ready || !usable || live.playing || Boolean(live.retryCommand)} onClick={live.step}><SkipForward size={15} />Advance one tick</button>
        <button className="text-button" disabled={!ready || !usable} onClick={live.stop}>Stop run</button>
        <button className="text-button" disabled={live.busy || live.status === 'loading'} onClick={live.refresh}><RefreshCw size={14} />Refresh telemetry</button>
      </div>
      <p className="control-caption">{live.run ? `Scenario: ${live.run.scenario.replaceAll('_', ' ')} · Tick ${live.run.last_tick_index} · Seed ${live.run.seed}` : 'Initialize a run, then press Play to see live fictional readings.'} · Play saves a tick approximately every 2 seconds, advancing simulated time by {live.run?.step_seconds || 60} seconds.</p>
      {live.active && !blocked && <p className="field-help">Stop this run before choosing a different scenario.</p>}
      {blocked && <p className="notice">An active run belongs to {crew.find(person => person.id === live.active.astronaut_id)?.display_name || 'another crew profile'}. Select that astronaut above and stop its run to free the simulator.</p>}
    </section>
    {live.status === 'loading' && <p role="status">Loading saved telemetry…</p>}
    {live.error && <div className="history-error panel" role="alert"><p>{live.error}</p>{live.retryCommand && <button className="button" disabled={live.busy} onClick={live.retryCommand}>Retry same command</button>}</div>}
    <div className="section-heading"><h2><Activity size={18} />Telemetry instruments</h2><span>API-backed · {live.playing ? 'Updating' : 'Stored observations'}</span></div>
    <section className="live-metrics" aria-label="Health and cabin indicators">{sensors.map(sensor => {
      const series = (sensor.environment ? environment : health).filter(value => value.indicator === sensor.indicator)
      const latest = series.at(-1) || (sensor.environment ? live.environment : live.health).find(value => value.indicator === sensor.indicator)
      return <article className="panel metric-card live-metric" key={sensor.indicator} style={{ '--sensor-color': sensor.color }} aria-label={sensor.label}>
        <div className="metric-top"><span>{sensor.label}</span><sensor.icon size={19} /></div>
        <div className="metric-value" key={`${latest?.id}:${latest?.value}`}><span className="reading-number">{latest?.value ?? 'No data'}</span><span>{sensor.unit}</span></div>
        <Sparkline points={series.slice(-24)} color={sensor.color} /><p className="sensor-time">{latest ? `${time(latest.observed_at)} UTC · Simulated` : 'Awaiting an explicit tick'}</p><small>{sensor.environment ? 'Mission cabin sensor' : 'Astronaut sensor'}</small>
      </article>
    })}</section>
    <div className="section-heading"><h2>Live trend charts</h2><span>Latest 120 observations per sensor · UTC</span></div>
    <div className="live-charts">{sensors.map(sensor => <Trend key={sensor.indicator} sensor={sensor} readings={sensor.environment ? environment : health} />)}</div>
    <section className="mission-summary" aria-label="Mission summary">
      <article className="panel"><span className="eyebrow cyan">LATEST CHECK-IN</span><h3>{checkin?.checkin_date || 'No check-in available'}</h3><p>{checkin ? `${checkin.context} · ${checkin.symptoms?.length || 0} reported symptoms` : 'Record a daily observation to add context.'}</p><Link to="/check-in">Open daily check-in</Link></article>
      <article className="panel"><span className="eyebrow cyan">EDUCATIONAL ASSESSMENT</span><h3>{assessment ? assessment.status.replaceAll('_', ' ') : 'No assessment available'}</h3><p>{assessment ? `Evaluated ${assessment.evaluated_at}` : 'No stored educational review for this astronaut.'}</p><p>Workflow context only; no clinical diagnosis or safety clearance.</p></article>
      <article className="panel"><span className="eyebrow cyan">MISSION ACTIVITY</span><h3>{live.playing ? 'Fictional telemetry streaming' : 'Mission context connected'}</h3><p>{health.length} astronaut readings · {environment.length} cabin readings in the displayed history.</p><p>{health.at(-1) ? `Latest astronaut observation: ${health.at(-1).observed_at}` : 'No telemetry observations yet.'}</p><Link to="/mission">Explore mission & crew</Link></article>
    </section>
    <RecentAlerts alerts={live.alerts} assessments={live.assessments} compact />
    <div className="notice"><p>All profiles are fictional. No live health monitoring or clinical assessment is active. Cabin radiation is not personal dosimetry. Refresh preserves saved data while the same backend process runs; backend restarts clear memory. Playback stops when you leave Overview.</p></div>
  </div>
}

function Sparkline({ points, color }) {
  if (!points.length) return <div className="spark-empty" aria-hidden="true" />
  const values = points.map(point => point.value), min = Math.min(...values), span = Math.max(...values) - min || 1
  const coordinates = values.map((value, index) => `${values.length === 1 ? 50 : index * 100 / (values.length - 1)},${27 - (value - min) / span * 22}`).join(' ')
  return <svg className="sparkline" viewBox="0 0 100 32" preserveAspectRatio="none" aria-hidden="true"><polyline points={coordinates} fill="none" stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" /></svg>
}

function Trend({ sensor, readings }) {
  const points = readings.filter(reading => reading.indicator === sensor.indicator).slice(-120).map(reading => ({ time: Date.parse(reading.observed_at), value: reading.value }))
  return <section className="panel live-chart" aria-label={`${sensor.label} trend`}><div className="panel-heading"><h3>{sensor.label}</h3><span>{sensor.unit} · UTC</span></div>
    {points.length ? <ResponsiveContainer width="100%" height={210} initialDimension={{ width: 500, height: 210 }}><AreaChart data={points} margin={{ top: 12, right: 15, bottom: 8, left: 0 }}>
      <defs><linearGradient id={`gradient-${sensor.indicator}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={sensor.color} stopOpacity={0.28} /><stop offset="100%" stopColor={sensor.color} stopOpacity={0.01} /></linearGradient></defs>
      <CartesianGrid stroke="#233149" strokeDasharray="3 6" vertical={false} />
      <XAxis dataKey="time" type="number" domain={['dataMin', 'dataMax']} tickFormatter={time} tick={{ fill: '#8d9db5', fontSize: 10 }} minTickGap={45} />
      <YAxis domain={sensor.domain} tick={{ fill: '#8d9db5', fontSize: 10 }} width={48} allowDataOverflow={false} />
      <Tooltip labelFormatter={value => `${new Date(value).toISOString().replace('T', ' ')} UTC`} formatter={value => [`${value} ${sensor.unit}`, sensor.label]} contentStyle={{ background: '#101d32', border: '1px solid #304562', borderRadius: 10, color: '#edf5ff' }} />
      <Area type="monotone" dataKey="value" stroke={sensor.color} strokeWidth={2} fill={`url(#gradient-${sensor.indicator})`} dot={points.length === 1} animationDuration={450} />
    </AreaChart></ResponsiveContainer> : <div className="trend-empty"><Activity size={26} /><p>No stored {sensor.label.toLowerCase()} history.</p><span>Start a run and advance a tick or press Play.</span></div>}
  </section>
}
