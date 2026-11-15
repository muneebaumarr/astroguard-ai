import { act, render, renderHook, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route, Outlet } from 'react-router'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { api } from '../src/services/api'
import { Dashboard } from '../src/pages/Dashboard'
import { useLiveDashboard } from '../src/hooks/useLiveDashboard'
import fixtures from '../../shared/fixtures/fictional.json'

const crew = fixtures.astronauts, mission = fixtures.missions[0]
let runs, health, environment, checkins, assessments
const copy = value => structuredClone(value)
const reading = (indicator, value, unit, run, tick) => ({ id: `${run.id}-${indicator}-${tick}`, indicator, value, unit,
  astronaut_id: run.astronaut_id, mission_id: run.mission_id, simulation_run_id: run.id, tick_index: tick,
  observed_at: new Date(Date.parse(run.simulation_start_at) + tick * 60000).toISOString() })

function seed() {
  const run = { id: 'e0629289-e8b4-493b-a90c-9a25b5953e9c', astronaut_id: crew[0].id, mission_id: mission.id,
    scenario: 'routine', seed: 42, status: 'paused', created_at: '2026-11-15T12:00:00Z', simulation_start_at: '2026-11-15T12:00:00Z', last_tick_index: -1, step_seconds: 60 }
  runs.push(run)
  return run
}

function generate(run) {
  const tick = ++run.last_tick_index
  health.push(...[['heart_rate', 72 + tick, 'bpm'], ['spo2', 98 - tick * .1, '%'], ['body_temperature', 36.7 + tick * .01, 'degC']].map(([indicator, value, unit]) => reading(indicator, value, unit, run, tick)))
  environment.push(...[['cabin_co2', 800 + tick, 'ppm'], ['radiation_dose_rate', 10 + tick, 'uSv/h']].map(([indicator, value, unit]) => reading(indicator, value, unit, run, tick)))
}

beforeEach(() => {
  runs = []; health = []; environment = []; checkins = []; assessments = []
  vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} })
  // jsdom has no layout; provide the chart container's measured laptop dimensions.
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({ width: 600, height: 210, top: 0, left: 0, right: 600, bottom: 210, x: 0, y: 0, toJSON: () => ({}) })
  vi.spyOn(api, 'healthTelemetry').mockImplementation(async id => ({ readings: copy(health.filter(value => value.astronaut_id === id).slice(-3)) }))
  vi.spyOn(api, 'environmentalTelemetry').mockImplementation(async () => ({ readings: copy(environment.slice(-2)) }))
  vi.spyOn(api, 'healthHistory').mockImplementation(async id => copy(health.filter(value => value.astronaut_id === id)))
  vi.spyOn(api, 'environmentHistory').mockImplementation(async () => copy(environment))
  vi.spyOn(api, 'simulationScenarios').mockResolvedValue([{ scenario: 'routine' }, { scenario: 'environmental_change' }])
  vi.spyOn(api, 'simulationRuns').mockImplementation(async () => copy(runs))
  vi.spyOn(api, 'checkins').mockImplementation(async () => copy(checkins))
  vi.spyOn(api, 'assessments').mockImplementation(async () => copy(assessments))
  vi.spyOn(api, 'simulationCommand').mockImplementation(async (action, id, body) => {
    if (action === 'create') { const run = seed(); Object.assign(run, body); return copy(run) }
    const run = runs.find(value => value.id === id)
    if (action === 'steps') { generate(run); return { run: copy(run) } }
    run.status = action === 'pause' ? 'paused' : 'stopped'
    return copy(run)
  })
})
afterEach(() => vi.useRealTimers())

function show(person = crew[0]) {
  const context = { status: 'ready', selectedId: person.id, astronauts: crew, profile: { status: 'ready', astronaut: person, mission } }
  return <MemoryRouter><Routes><Route element={<Outlet context={context} />}><Route path="/" element={<Dashboard />} /></Route></Routes></MemoryRouter>
}
async function hook() {
  const rendered = renderHook(() => useLiveDashboard(crew[0].id, mission.id))
  await waitFor(() => expect(rendered.result.current.status).toBe('ready'))
  return rendered
}

test('loads historical health and separate cabin charts, actual values, units, timestamps and summary', async () => {
  const run = seed(); generate(run); generate(run)
  checkins.push({ checkin_date: '2026-11-15', observed_at: '2026-11-15T10:00:00Z', context: 'resting', symptoms: [] })
  assessments.push({ evaluated_at: '2026-11-15T10:00:00Z', status: 'insufficient_data' })
  render(show())
  const heart = await screen.findByRole('article', { name: 'Heart rate' })
  await waitFor(() => expect(heart).toHaveTextContent('73'))
  expect(heart).toHaveTextContent('bpm')
  expect(heart).toHaveTextContent('12:01:00 UTC')
  expect(screen.getByRole('article', { name: 'Oxygen saturation' })).toHaveTextContent('97.9')
  expect(screen.getByRole('article', { name: 'Body temperature' })).toHaveTextContent('°C')
  expect(screen.getByRole('article', { name: 'Cabin CO₂' })).toHaveTextContent('801')
  expect(screen.getByRole('article', { name: 'Radiation dose rate' })).toHaveTextContent('uSv/h')
  expect(screen.getAllByRole('region', { name: /trend$/ })).toHaveLength(5)
  await waitFor(() => expect(screen.getByRole('region', { name: 'Heart rate trend' }).querySelector('svg')).toBeInTheDocument())
  expect(screen.getByText('2026-11-15')).toBeInTheDocument()
  expect(screen.getByText('insufficient data')).toBeInTheDocument()
  expect(api.simulationCommand).not.toHaveBeenCalled()
})

test('empty dashboard initializes selected scenario and manual tick displays backend results', async () => {
  const user = userEvent.setup()
  render(show())
  await waitFor(() => expect(screen.getByRole('button', { name: 'Start simulation' })).toBeEnabled())
  expect(screen.getAllByText('No data')).toHaveLength(5)
  expect(screen.getAllByText(/^No stored .* history\.$/)).toHaveLength(5)
  expect(screen.getByRole('button', { name: 'Play', exact: true })).toBeDisabled()
  await user.selectOptions(screen.getByRole('combobox', { name: 'Scenario' }), 'environmental_change')
  await user.click(screen.getByRole('button', { name: 'Start simulation' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Advance one tick' })).toBeEnabled())
  expect(api.simulationCommand.mock.calls[0][2]).toMatchObject({ scenario: 'environmental_change', astronaut_id: crew[0].id, seed: 42 })
  await user.click(screen.getByRole('button', { name: 'Advance one tick' }))
  await waitFor(() => expect(screen.getByRole('article', { name: 'Heart rate' })).toHaveTextContent('72'))
  expect(api.simulationCommand.mock.calls[1][2]).toEqual({ steps: 1 })
})

test('play requests automatic ticks, ignores duplicate play, and pause cancels future ticks', async () => {
  seed(); const { result } = await hook()
  vi.useFakeTimers()
  act(() => { result.current.play(); result.current.play() })
  await act(() => vi.advanceTimersByTimeAsync(2000))
  expect(api.simulationCommand).toHaveBeenCalledTimes(1)
  expect(result.current.history).toHaveLength(3)
  await act(() => vi.advanceTimersByTimeAsync(2000))
  expect(api.simulationCommand).toHaveBeenCalledTimes(2)
  expect(result.current.health[0].value).toBe(73)
  act(() => result.current.pause())
  await act(() => vi.advanceTimersByTimeAsync(10000))
  expect(result.current.playing).toBe(false)
  expect(api.simulationCommand).toHaveBeenCalledTimes(2)
})

test('a slow tick never overlaps another, and pausing during its request does not schedule more', async () => {
  seed(); const { result } = await hook()
  let release
  api.simulationCommand.mockImplementation(() => new Promise(resolve => { release = resolve }))
  vi.useFakeTimers()
  act(() => result.current.play())
  await act(() => vi.advanceTimersByTimeAsync(12000))
  expect(api.simulationCommand).toHaveBeenCalledTimes(1)
  act(() => result.current.pause())
  await act(async () => release({ run: copy(runs[0]) }))
  await act(() => vi.advanceTimersByTimeAsync(6000))
  expect(api.simulationCommand).toHaveBeenCalledTimes(1)
})

test('unmount cancels automatic ticks and aborts an outstanding mutation', async () => {
  seed(); const { result, unmount } = await hook()
  api.simulationCommand.mockImplementation(() => new Promise(() => {}))
  vi.useFakeTimers()
  act(() => result.current.play())
  await act(() => vi.advanceTimersByTimeAsync(2000))
  const signal = api.simulationCommand.mock.calls[0][4]
  unmount()
  expect(signal.aborted).toBe(true)
  await act(() => vi.advanceTimersByTimeAsync(10000))
  expect(api.simulationCommand).toHaveBeenCalledTimes(1)
})

test('a failed automatic tick stops playback and reuses the UUID command key on retry', async () => {
  seed(); const { result } = await hook()
  api.simulationCommand.mockRejectedValueOnce(new Error('Connection lost'))
  vi.useFakeTimers()
  act(() => result.current.play())
  await act(() => vi.advanceTimersByTimeAsync(2000))
  expect(result.current.playing).toBe(false)
  expect(result.current.error).toContain('Playback stopped')
  await act(() => vi.advanceTimersByTimeAsync(10000))
  expect(api.simulationCommand).toHaveBeenCalledTimes(1)
  await act(async () => result.current.retryCommand())
  expect(api.simulationCommand.mock.calls[0][3]).toMatch(/^[0-9a-f-]{36}$/)
  expect(api.simulationCommand.mock.calls[1][3]).toBe(api.simulationCommand.mock.calls[0][3])
  expect(result.current.history).toHaveLength(3)
})

test('acknowledged tick followed by GET failure only retries loading, not the mutation', async () => {
  seed(); const { result } = await hook()
  api.healthHistory.mockRejectedValueOnce(new Error('History unavailable'))
  await act(async () => result.current.step())
  expect(result.current.error).toContain('History unavailable')
  expect(result.current.retryCommand).toBeNull()
  await act(async () => result.current.refresh())
  expect(api.simulationCommand).toHaveBeenCalledTimes(1)
  expect(result.current.history).toHaveLength(3)
})

test('saved readings survive remount without auto-play or generating new readings', async () => {
  const run = seed(); generate(run)
  const first = render(show())
  await waitFor(() => expect(screen.getByRole('article', { name: 'Heart rate' })).toHaveTextContent('72'))
  first.unmount(); render(show())
  await waitFor(() => expect(screen.getByRole('article', { name: 'Heart rate' })).toHaveTextContent('72'))
  expect(screen.getByText('Playback paused')).toBeInTheDocument()
  expect(api.simulationCommand).not.toHaveBeenCalled()
})

test('switching astronauts cancels playback and clears old astronaut readings', async () => {
  const run = seed(); generate(run)
  const user = userEvent.setup(), rendered = render(show())
  await waitFor(() => expect(screen.getByRole('button', { name: 'Play', exact: true })).toBeEnabled())
  await user.click(screen.getByRole('button', { name: 'Play', exact: true }))
  rendered.rerender(show(crew[1]))
  await waitFor(() => expect(screen.getByRole('article', { name: 'Heart rate' })).toHaveTextContent('No data'))
  expect(screen.getByText('Playback paused')).toBeInTheDocument()
  expect(screen.getByText(/An active run belongs to/)).toBeInTheDocument()
  vi.useFakeTimers()
  await act(() => vi.advanceTimersByTimeAsync(6000))
  expect(api.simulationCommand).not.toHaveBeenCalled()
  expect(within(screen.getByRole('article', { name: 'Heart rate' })).queryByText('72')).not.toBeInTheDocument()
})

test('load error is explicit and refresh recovers without mock readings', async () => {
  api.healthHistory.mockRejectedValueOnce(new Error('History unavailable'))
  render(show())
  expect(await screen.findByRole('alert')).toHaveTextContent('History unavailable')
  await userEvent.setup().click(screen.getByRole('button', { name: 'Refresh telemetry' }))
  await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
  expect(screen.getAllByText('No data')).toHaveLength(5)
})

test('a delayed old history response cannot replace the newly selected astronaut', async () => {
  const run = seed(); generate(run)
  let release
  api.healthHistory.mockImplementationOnce(() => new Promise(resolve => { release = resolve }))
  const rendered = render(show())
  await waitFor(() => expect(release).toBeTypeOf('function'))
  rendered.rerender(show(crew[1]))
  await waitFor(() => expect(screen.queryByText('Loading saved telemetry…')).not.toBeInTheDocument())
  await act(async () => release(copy(health)))
  expect(screen.getByRole('article', { name: 'Heart rate' })).toHaveTextContent('No data')
  expect(api.healthHistory).toHaveBeenLastCalledWith(crew[1].id, expect.any(AbortSignal))
})

test('double initialization is locked and a lost create response retries the exact timestamp and key', async () => {
  const { result } = await hook()
  let reject
  api.simulationCommand.mockImplementationOnce(() => new Promise((resolve, fail) => { reject = fail }))
  let first
  act(() => { first = result.current.start('routine'); result.current.start('routine') })
  expect(api.simulationCommand).toHaveBeenCalledTimes(1)
  await act(async () => { reject(new Error('Lost create response')); await first })
  const original = api.simulationCommand.mock.calls[0]
  await act(async () => result.current.start('routine'))
  expect(api.simulationCommand.mock.calls[1].slice(0, 4)).toEqual(original.slice(0, 4))
})

test('a backend-running run is paused through the existing API before an explicit tick', async () => {
  seed().status = 'running'
  const { result } = await hook()
  await act(async () => result.current.step())
  expect(api.simulationCommand.mock.calls.map(call => call[0])).toEqual(['pause', 'steps'])
  expect(result.current.run.status).toBe('paused')
  expect(result.current.history).toHaveLength(3)
})
