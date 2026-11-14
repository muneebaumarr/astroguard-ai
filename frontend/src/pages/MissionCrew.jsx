import { useOutletContext } from 'react-router'
import { ArrowRight, Orbit, UserRound } from 'lucide-react'
import { PageHeading } from '../components/common/PageHeading'
import { ProfileGate } from '../components/common/ProfileGate'
import { DemoBadge } from '../components/common/States'

export function MissionCrew() {
  const data = useOutletContext()
  const mission = data.profile.mission
  const astronaut = data.profile.astronaut
  return <><PageHeading title="Mission & crew">The people and environment behind your workspace.</PageHeading>
    <ProfileGate data={data}>
      <section className="panel mission-detail"><div className="panel-heading"><h2><Orbit size={20} />{mission?.name}</h2><DemoBadge /></div>
        <p>{mission?.description}</p><dl className="detail-grid"><div><dt>Mission environment</dt><dd>{mission?.environment.replaceAll('_', ' ')}</dd></div>
          <div><dt>Mission start · UTC</dt><dd>{mission && new Date(mission.started_at).toISOString().slice(0, 10)}</dd></div>
          <div><dt>Selected crew member</dt><dd>{astronaut?.display_name}</dd></div></dl></section>
      <div className="section-heading"><h2>Crew profiles</h2><span>{data.astronauts.length} fictional profiles</span></div>
      <section className="crew-grid" aria-label="Crew profiles">{data.astronauts.map(person => {
        const assignment = data.missions.find(item => item.id === person.mission_id)
        const selected = person.id === data.selectedId
        return <article className={`panel crew-card ${selected ? 'selected' : ''}`} key={person.id}>
          <div className="crew-avatar"><UserRound size={29} /></div><DemoBadge />
          <h2>{person.display_name}</h2><p>{person.role}</p><span className="muted">{assignment?.name || 'Mission unavailable'}</span>
          <button className="support-link" aria-pressed={selected} onClick={() => data.setSelectedId(person.id)}>
            {selected ? 'Selected profile' : 'Select profile'}<ArrowRight size={16} /></button>
        </article>
      })}</section>
    </ProfileGate>
  </>
}
