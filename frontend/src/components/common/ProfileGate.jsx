import { EmptyState, ErrorState, LoadingState } from './States'

export function ProfileGate({ data, children }) {
  if (data.status === 'loading') return <LoadingState />
  if (data.status === 'error') return <ErrorState message={data.error} onRetry={data.retry} />
  if (!data.astronauts.length) return <EmptyState title="No crew profiles">No fictional astronauts are available from the API.</EmptyState>
  if (data.profile.status === 'error') return <ErrorState message={data.profile.error} onRetry={data.retry} />
  if (data.profile.status !== 'ready') return <LoadingState>Loading selected crew profile…</LoadingState>
  return children
}
