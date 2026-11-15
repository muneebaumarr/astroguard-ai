import { useEffect, useState } from 'react'
import { api } from '../services/api'

export function useEducation(kind) {
  const [view, setView] = useState({ status: 'loading', items: [], error: '' })
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    let current = true
    setView({ status: 'loading', items: [], error: '' })
    api[kind](controller.signal).then(items => { if (current) setView({ status: 'ready', items, error: '' }) })
      .catch(error => { if (current && error.name !== 'AbortError') setView({ status: 'error', items: [], error: error.message }) })
    return () => { current = false; controller.abort() }
  }, [kind, revision])
  return { ...view, refresh: () => setRevision(value => value + 1) }
}
