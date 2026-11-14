import { useOutletContext, Link } from 'react-router'
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
    <PageHeading title="Crew health overview" aside={<span className="outline-label"><Radio size={14} />Monitoring inactive</span>}>
      A clearer view of your health. Wherever the mission takes you.
    </PageHeading>
    <ProfileGate data={data}>
      <section className="mission-card panel" aria-label="Selected astronaut">
        <div className="mission-copy"><span className="eyebrow cyan">YOUR MISSION. YOUR WELLBEING.</span>
          <h2>Welcome aboard,<br /><span>{astronaut?.display_name}.</span></h2>
          <p>Your personal health workspace is ready. Measurements will appear here when monitoring becomes available.</p>
          <div className="mission-facts"><div><span>MISSION</span><strong>{mission?.name}</strong></div>
            <div><span>ENVIRONMENT</span><strong>{mission?.environment.replaceAll('_', ' ')}</strong></div>
            <div><span>CREW ROLE</span><strong>{astronaut?.role}</strong></div></div>
        </div><MissionGraphic />
      </section>
      <div className="section-heading"><h2><Activity size={18} />Health indicators</h2><span>Awaiting observations</span></div>
      <section className="metrics-grid" aria-label="Health indicators">
        {metrics.map(({ label, unit, icon: Icon }) => <article className="metric-card panel" key={label}>
          <div className="metric-top"><span>{label}</span><Icon size={18} strokeWidth={1.6} /></div>
          <div className="metric-value">No data <span>{unit}</span></div>
          <div className="metric-bottom"><CircleDashed size={12} />No measurement available</div>
        </article>)}
      </section>
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

function ChartPlaceholder() {
  return <div className="chart-placeholder" aria-hidden="true"><span /><span /><span /><span /><span /></div>
}
