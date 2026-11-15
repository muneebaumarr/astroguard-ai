import { useEffect, useState } from 'react'
import { useOutletContext, Link } from 'react-router'
import { api } from '../services/api'
import { Activity, ArrowRight, Droplets, Heart, Moon, Thermometer, Wind, Radio, ShieldCheck, CircleDashed, Orbit } from 'lucide-react'
import { PageHeading } from '../components/common/PageHeading'
import { ProfileGate } from '../components/common/ProfileGate'

const metrics = [
  { label: 'Heart rate', unit: 'bpm', icon: Heart },
  { label: 'Blood oxygen', unit: '% SpO₂', icon: Wind },
  { label: 'Body temperature', unit: '°C', icon: Thermometer },
  { label: 'Blood pressure', unit: 'mmHg', icon: Activity },
  { label: 'Blood glucose', unit: 'mg/dL', icon: Droplets },
  { label: 'Sleep duration', unit: 'hours', icon: Moon },
]

function MissionGraphic() {
  return <div className="mission-graphic" aria-hidden="true"><div className="planet" /><div className="orbit orbit-one" />
    <div className="orbit orbit-two" /><span className="satellite" /><span className="orbit-dot" />
    <span className="graphic-cross cross-one">+</span><span className="graphic-cross cross-two">+</span><span className="graphic-caption">ASTROGUARD / CREW FIRST</span></div>
}

export function Dashboard() {
  const data = useOutletContext()
  const astronaut = data.profile.astronaut
  const mission = data.profile.mission
  return <>
    <PageHeading title="Crew health overview" aside={<Link className="outline-label" to="/demo"><Radio size={14} />Open Mission Simulator</Link>}>
      A clearer view of your health. Wherever the mission takes you.
    </PageHeading>
    <ProfileGate data={data}>
      <section className="mission-card panel" aria-label="Selected astronaut">
        <div className="mission-copy"><span className="eyebrow cyan">YOUR MISSION. YOUR WELLBEING.</span>
          <h2>Welcome aboard,<br /><span>{astronaut?.display_name}.</span></h2>
          <p>Explore saved fictional telemetry below. Open Mission Simulator and advance a tick to generate sensor readings.</p>
          <div className="mission-facts"><div><span>MISSION</span><strong>{mission?.name}</strong></div>
            <div><span>ENVIRONMENT</span><strong>{mission?.environment.replaceAll('_', ' ')}</strong></div>
            <div><span>CREW ROLE</span><strong>{astronaut?.role}</strong></div></div>
        </div><MissionGraphic />
      </section>
      {data.profile.status === 'ready' && <DashboardTelemetry key={astronaut.id} astronautId={astronaut.id} missionId={mission.id} />}
      <div className="lower-grid">
        <section className="panel trend-panel"><div className="panel-heading"><h2>Health trends</h2><Link to="/history">View history <ArrowRight size={14} /></Link></div>
          <div className="chart-empty"><ChartPlaceholder /><strong>Your story starts with an observation</strong>
            <p>Historical charts will appear when measurement history is available.</p><span className="outline-label">No data</span></div>
        </section>
        <section className="panel readiness-panel"><div className="panel-heading"><h2>Crew support</h2><ShieldCheck size={18} /></div>
          <div className="support-row"><span className="support-icon"><ShieldCheck size={19} /></span><div><strong>No assessment available</strong><p>Health evaluation is not active.</p></div></div>
          <div className="support-row"><span className="support-icon"><Orbit size={19} /></span><div><strong>Mission context connected</strong><p>Fictional crew and mission profiles loaded from the API.</p></div></div>
          <Link className="support-link" to="/mission">Explore mission & crew<ArrowRight size={16} /></Link>
        </section>
      </div>
      <div className="notice"><ShieldCheck size={17} /><p><strong>A demonstration built around understanding.</strong> All profiles are fictional. No live health monitoring or clinical assessment is active.</p></div>
    </ProfileGate>
  </>
}

function DashboardTelemetry({ astronautId, missionId }) {
  const [view, setView] = useState({ status: 'loading', health: [], environment: [] })
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    let current = true
    setView({ status: 'loading', health: [], environment: [] })
    Promise.all([api.healthTelemetry(astronautId, controller.signal), api.environmentalTelemetry(missionId, controller.signal)])
      .then(([health, environment]) => { if (current) setView({ status: 'ready', health: health.readings, environment: environment.readings }) })
      .catch(error => { if (current && error.name !== 'AbortError') setView({ status: 'error', error: error.message, health: [], environment: [] }) })
    return () => { current = false; controller.abort() }
  }, [astronautId, missionId, revision])
  const healthKeys = ['heart_rate', 'spo2', 'body_temperature']
  function cards(definitions, readings) {
    return definitions.map(({ label, unit, icon: Icon, indicator }, index) => {
      const reading = readings.find(item => item.indicator === (indicator || healthKeys[index]))
      return <article className="metric-card panel" key={label}>
        <div className="metric-top"><span>{label}</span><Icon size={18} strokeWidth={1.6} /></div>
        <div className="metric-value">{reading ? reading.value : 'No data'} <span>{reading?.unit || unit}</span></div>
        <div className="metric-bottom"><CircleDashed size={12} />{reading ? `Simulated · ${reading.observed_at}` : 'No measurement available'}</div>
      </article>
    })
  }
  return <>
    <div className="section-heading"><h2><Activity size={18} />Health indicators</h2><button type="button" onClick={() => setRevision(value => value + 1)} disabled={view.status === 'loading'}>Refresh telemetry</button></div>
    <p>Fictional simulated data. Readings persist until the backend restarts. <Link to="/demo">Start or advance a simulation</Link>.</p>
    {view.status === 'loading' && <p role="status">Loading saved telemetry…</p>}
    {view.status === 'error' && <p role="alert">{view.error}</p>}
    <section className="metrics-grid" aria-label="Health indicators">{cards(metrics, view.health)}</section>
    <div className="section-heading"><h2>Mission environment</h2><span>Shared cabin readings for this mission</span></div>
    <section className="metrics-grid" aria-label="Mission environment">{cards([
      { label: 'Cabin CO2', indicator: 'cabin_co2', unit: 'ppm', icon: Wind },
      { label: 'Radiation dose rate', indicator: 'radiation_dose_rate', unit: 'uSv/h', icon: Radio },
    ], view.environment)}</section>
  </>
}

function ChartPlaceholder() {
  return <div className="chart-placeholder" aria-hidden="true"><span /><span /><span /><span /><span /></div>
}
