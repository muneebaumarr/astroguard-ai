import { useEffect, useState } from 'react'
import { Link, useOutletContext, useSearchParams } from 'react-router'
import { BookOpen } from 'lucide-react'
import { PageHeading } from '../components/common/PageHeading'
import { EducationSources, EducationText, educationDisclaimer } from '../components/common/EducationContent'
import { useEducation } from '../hooks/useEducation'
import { api } from '../services/api'
import { guidanceSuggestions } from '../services/guidanceSuggestions'

export function Guidance() {
  const data = useOutletContext(), view = useEducation('guidance'), [params, setParams] = useSearchParams()
  const hazard = params.get('hazard'), selected = params.get('topic')
  const articles = view.items.filter(article => !hazard || article.hazard_slugs.includes(hazard))
  return <><PageHeading title="Health guidance">A spaceflight learning library with explainable fictional topic suggestions.</PageHeading>
    <div className="panel education-banner"><span className="eyebrow cyan">EDUCATION · NOT INDIVIDUAL MEDICAL ADVICE</span><p>{educationDisclaimer}</p></div>
    {data.profile.status === 'ready' ? <ContextSuggestions key={data.selectedId} astronaut={data.profile.astronaut} articles={view.items} /> : <p className="notice">Select a loaded fictional crew profile to see topic suggestions. The general library remains available below.</p>}
    <div className="section-heading"><h2><BookOpen size={18} />Educational library</h2><button className="text-button" disabled={view.status === 'loading'} onClick={view.refresh}>Refresh guidance</button></div>
    {hazard && <p className="notice">Showing topics linked to {hazard.replaceAll('_', ' ')}. <button className="text-button" onClick={() => setParams({})}>Show all topics</button></p>}
    {view.status === 'loading' && <p role="status">Loading educational guidance…</p>}
    {view.status === 'error' && <div className="history-error panel" role="alert"><p>{view.error}</p><button className="button" onClick={view.refresh}>Retry guidance</button></div>}
    {view.status === 'ready' && !articles.length && <div className="panel education-empty">No educational topics match this selection.</div>}
    <div className="guidance-grid">{articles.map(article => <article className="panel guidance-card" key={article.slug}><span className="eyebrow cyan">SPACEFLIGHT LEARNING</span><h2>{article.title}</h2><p>{article.educational_text.split('\n\n')[0]}</p>
      <button className="text-button" aria-expanded={selected === article.slug} aria-controls={`topic-${article.slug}`} onClick={() => setParams({ ...(hazard ? { hazard } : {}), ...(selected === article.slug ? {} : { topic: article.slug }) })}>{selected === article.slug ? 'Close topic' : 'Read topic'}: {article.title}</button>
      {selected === article.slug && <div id={`topic-${article.slug}`}><EducationText text={article.educational_text} /><div className="education-limit"><h3>Educational limitations</h3><p>{article.limitations}</p></div><EducationSources references={article.references} reviewedOn={article.reviewed_on} />
        <div className="education-links">{article.hazard_slugs.map(slug => <Link key={slug} to={`/hazards?hazard=${slug}`}>Explore {slug.replaceAll('_', ' ')} →</Link>)}</div></div>}
    </article>)}</div>
    {view.status === 'ready' && selected && !articles.some(article => article.slug === selected) && <p className="notice">The requested topic is unavailable in this selection. Choose a topic above.</p>}
  </>
}

function ContextSuggestions({ astronaut, articles }) {
  const [view, setView] = useState({ status: 'loading', suggestions: [], error: '' }), [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    let current = true
    setView({ status: 'loading', suggestions: [], error: '' })
    Promise.all([api.assessments(astronaut.id, controller.signal), api.alerts(astronaut.id, controller.signal), api.checkins(astronaut.id, controller.signal), api.healthTelemetry(astronaut.id, controller.signal)])
      .then(([assessments, alerts, checkins, telemetry]) => {
        if (current) setView({ status: 'ready', error: '', suggestions: guidanceSuggestions({ astronautId: astronaut.id, articles, assessments, alerts, checkins, readings: telemetry.readings }) })
      }).catch(error => { if (current && error.name !== 'AbortError') setView({ status: 'error', error: error.message, suggestions: [] }) })
    return () => { current = false; controller.abort() }
  }, [astronaut.id, articles, revision])
  return <section className="panel context-guidance" aria-label="Fictional topic suggestions"><div className="panel-heading"><h2>Learning context for {astronaut.display_name}</h2><button className="text-button" disabled={view.status === 'loading'} onClick={() => setRevision(value => value + 1)}>Refresh suggestions</button></div>
    <p>Frontend educational topic suggestions from this astronaut’s API records. These are not personalized treatment or evidence that a hazard occurred.</p>
    {view.status === 'loading' && <p role="status">Loading selected astronaut context…</p>}
    {view.status === 'error' && <p role="alert">{view.error} General educational topics remain available.</p>}
    {view.status === 'ready' && !view.suggestions.length && <p>No relevant recorded context is available for topic suggestions. Explore the general library below.</p>}
    <ul>{view.suggestions.map(suggestion => <li key={suggestion.slug}><Link to={`/guidance?topic=${suggestion.slug}`}>{articles.find(article => article.slug === suggestion.slug)?.title}</Link><ul>{suggestion.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul></li>)}</ul>
  </section>
}
