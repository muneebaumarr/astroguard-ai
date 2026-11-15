import { Link, useSearchParams } from 'react-router'
import { Radio, Users, Globe, Orbit, Shield } from 'lucide-react'
import { PageHeading } from '../components/common/PageHeading'
import { useEducation } from '../hooks/useEducation'
import { EducationSources, EducationText, educationDisclaimer } from '../components/common/EducationContent'

const icons = { space_radiation: Radio, isolation_confinement: Users, distance_from_earth: Globe, gravity_fields: Orbit, hostile_closed_environments: Shield }

export function Hazards() {
  const view = useEducation('hazards'), [params, setParams] = useSearchParams()
  const slug = params.get('hazard')
  const selected = view.items.find(item => item.slug === slug) || (!slug ? view.items[0] : null)
  return <><PageHeading title="Spaceflight hazards">Explore the five hazards of human spaceflight through general NASA educational context.</PageHeading>
    <div className="education-banner panel"><span className="eyebrow cyan">NASA EDUCATIONAL CONTEXT · NOT LIVE HAZARD DETECTION</span><p>{educationDisclaimer}</p></div>
    <div className="section-heading"><h2>Five hazards. One connected mission.</h2><button className="text-button" disabled={view.status === 'loading'} onClick={view.refresh}>Refresh hazards</button></div>
    {view.status === 'loading' && <p role="status">Loading spaceflight hazards…</p>}
    {view.status === 'error' && <div className="history-error panel" role="alert"><p>{view.error}</p><button className="button" onClick={view.refresh}>Retry hazards</button></div>}
    {view.status === 'ready' && !view.items.length && <div className="panel education-empty">No hazard education is available.</div>}
    <div className="hazard-grid" aria-label="Hazard categories">{view.items.map((hazard, index) => {
      const Icon = icons[hazard.slug] || Shield
      return <button key={hazard.slug} className={`panel hazard-choice ${selected?.slug === hazard.slug ? 'selected' : ''}`} aria-pressed={selected?.slug === hazard.slug} onClick={() => setParams({ hazard: hazard.slug })}><span className="hazard-number">0{index + 1}</span><Icon size={28} /><strong>{hazard.title}</strong><span>Explore educational context →</span></button>
    })}</div>
    {selected && <section className="panel hazard-detail" aria-label={`${selected.title} details`}><span className="eyebrow cyan">HAZARD EXPLORER</span><h2>{selected.title}</h2><EducationText text={selected.description} />
      <div className="education-limit"><h3>Monitoring considerations and limits</h3><p>{selected.monitoring_limitations}</p></div><EducationSources references={selected.references} />
      <Link className="button" to={`/guidance?hazard=${selected.slug}`}>Explore related educational topics</Link></section>}
    {view.status === 'ready' && slug && !selected && <p className="notice">This hazard category is unavailable. Select a category above.</p>}
  </>
}
