import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'

export function useMissionData() {
  const [attempt, setAttempt] = useState(0)
  const [data, setData] = useState({ status: 'loading', astronauts: [], missions: [], health: null, error: null })
  const [selectedId, setSelectedId] = useState('')
  const [profile, setProfile] = useState({ status: 'idle', astronaut: null, mission: null, error: null })

  useEffect(() => {
    const controller = new AbortController()
    let current = true
    setData({ status: 'loading', astronauts: [], missions: [], health: null, error: null })
    Promise.all([api.health(controller.signal), api.missions(controller.signal), api.astronauts(controller.signal)])
      .then(([health, missions, astronauts]) => {
        if (!current) return
        setData({ status: 'ready', health, missions, astronauts, error: null })
        setSelectedId(previous => astronauts.some(a => a.id === previous) ? previous : (astronauts[0]?.id || ''))
      }).catch(error => {
        if (current && error.name !== 'AbortError') {
          setData({ status: 'error', astronauts: [], missions: [], health: null, error: error.message })
        }
      })
    return () => { current = false; controller.abort() }
  }, [attempt])

  useEffect(() => {
    if (data.status !== 'ready' || !selectedId) {
      setProfile({ status: 'idle', astronaut: null, mission: null, error: null })
      return
    }
    const controller = new AbortController()
    let current = true
    setProfile({ status: 'loading', astronaut: null, mission: null, error: null })
    api.astronaut(selectedId, controller.signal)
      .then(async astronaut => ({ astronaut, mission: await api.mission(astronaut.mission_id, controller.signal) }))
      .then(result => {
        if (current) setProfile({ status: 'ready', ...result, error: null })
      }).catch(error => {
        if (current && error.name !== 'AbortError') setProfile({ status: 'error', astronaut: null, mission: null, error: error.message })
      })
    return () => { current = false; controller.abort() }
  }, [selectedId, data.status, attempt])

  const retry = useCallback(() => setAttempt(value => value + 1), [])
  // A selection render must never display the previous astronaut while its effect catches up.
  const visibleProfile = profile.astronaut?.id && profile.astronaut.id !== selectedId
    ? { status: 'loading', astronaut: null, mission: null, error: null } : profile
  return { ...data, profile: visibleProfile, selectedId, setSelectedId, retry }
}
