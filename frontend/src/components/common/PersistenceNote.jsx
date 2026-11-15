export function PersistenceNote({ adapter }) {
  return <span>{adapter === 'sqlite' ? 'SQLite storage: committed records survive browser refresh and backend restarts.'
    : adapter === 'memory' ? 'Memory storage: browser refresh preserves records; backend restarts clear memory.'
      : 'Record persistence depends on the configured storage backend.'}</span>
}
