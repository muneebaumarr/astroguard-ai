import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'

export function useCheckinHistory(astronautId) {
  const [generation, setGeneration] = useState(0)
  const [history, setHistory] = useState({ status: 'loading', checkins: [], assessments: [], error: null })
  useEffect(() => {
    let current = true
    const controller = new AbortController()
    setHistory({ status: 'loading', checkins: [], assessments: [], error: null })
    Promise.all([api.checkins(astronautId, controller.signal), api.assessments(astronautId, controller.signal)])
      .then(([checkins, assessments]) => {
        if (current) setHistory({ status: 'ready', checkins: [...checkins].sort((a, b) => b.observed_at.localeCompare(a.observed_at) || b.id.localeCompare(a.id)), assessments, error: null })
      }).catch(error => {
        if (current && error.name !== 'AbortError') setHistory({ status: 'error', checkins: [], assessments: [], error: error.message })
      })
    return () => { current = false; controller.abort() }
  }, [astronautId, generation])
  const refresh = useCallback(() => setGeneration(value => value + 1), [])
  return { ...history, refresh }
}
