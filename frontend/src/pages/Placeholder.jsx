import { Link } from 'react-router'
import { PageHeading } from '../components/common/PageHeading'
import { EmptyState } from '../components/common/States'

export function Placeholder({ title, description, empty }) {
  return <><PageHeading title={title}>{description}</PageHeading><section className="panel placeholder-panel">
    <EmptyState title="Workspace coming soon">{empty}</EmptyState>
    <p className="placeholder-note">Fictional educational demo · No health data is generated here.</p>
    <Link className="button" to="/">Back to overview</Link>
  </section></>
}

export function NotFound() {
  return <><PageHeading title="Page not found">This address is outside the crew workspace.</PageHeading>
    <Link className="button" to="/">Return to overview</Link></>
}
