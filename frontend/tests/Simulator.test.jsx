import { act, cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, test, vi } from 'vitest'
import { App } from '../src/app/App'
import fixtures from '../../shared/fixtures/fictional.json'

const crew = fixtures.astronauts
const mission = fixtures.missions[0]
const scenarios = ['routine', 'exercise_recovery', 'reduced_sleep_stress', 'unusual_health_trend', 'environmental_change']
const ok = data => ({ ok: true, status: 200, json: async () => structuredClone(data) })
const page = items => ({ items, total: items.length, limit: 100, offset: 0 })
let runs, health, environment, postBehavior

function mutate(path, body) {
  if (path === '/api/v1/simulation/runs') {
    const run = { ...body, id: crypto.randomUUID(), mission_id: mission.id, created_at: '2026-11-15T12:00:00Z',
      status: 'paused', last_tick_index: -1, started_at: null, scenario_version: 'telemetry-v1' }
    runs.push(run)
    return ok(run)
  }
  const run = runs.find(run => path.includes(run.id))
  if (path.endsWith('/stop')) { run.status = 'stopped'; return ok(run) }
  if (path.endsWith('/pause')) { run.status = 'paused'; return ok(run) }
  run.last_tick_index += 1
  const common = { simulation_run_id: run.id, source: 'simulated', tick_index: run.last_tick_index,
    observed_at: new Date(Date.parse(run.simulation_start_at) + run.last_tick_index * 60000).toISOString() }
  for (const [indicator, value, unit] of [['heart_rate', 72 + run.last_tick_index, 'bpm'], ['spo2', 98, '%'], ['body_temperature', 36.7, 'degC']]) {
    health.push({ ...common, id: crypto.randomUUID(), astronaut_id: run.astronaut_id, indicator, value, unit })
  }
  for (const [indicator, value, unit] of [['cabin_co2', 800, 'ppm'], ['radiation_dose_rate', 10, 'uSv/h']]) {
    environment.push({ ...common, id: crypto.randomUUID(), mission_id: mission.id, indicator, value, unit })
  }
  return ok({ run, generated_health_count: 3, generated_environmental_count: 2 })
}

function respond(url, options = {}) {
  const parsed = new URL(url), path = parsed.pathname
  if (options.method === 'POST') return postBehavior ? postBehavior(path, JSON.parse(options.body || 'null'), options) : mutate(path, JSON.parse(options.body || 'null'))
  if (path.endsWith('/health')) return ok({ status: 'ok' })
  if (path === '/api/v1/missions') return ok(page([mission]))
  if (path === '/api/v1/astronauts') return ok(page(crew))
  if (path === `/api/v1/missions/${mission.id}`) return ok(mission)
  const person = crew.find(person => path === `/api/v1/astronauts/${person.id}`)
  if (person) return ok(person)
  if (path === '/api/v1/simulation/scenarios') return ok(page(scenarios.map(scenario => ({ scenario, version: 'telemetry-v1', description: `Fictional ${scenario} illustration` }))))
  if (path === '/api/v1/simulation/runs') return ok(page(runs))
  if (path.startsWith('/api/v1/simulation/runs/')) return ok(runs.find(run => path.endsWith(run.id)))
  const runId = parsed.searchParams.get('simulation_run_id')
  if (path.endsWith('/environmental-readings')) return ok(page(environment.filter(value => value.simulation_run_id === runId)))
  if (path.endsWith('/readings')) return ok(page(health.filter(value => value.simulation_run_id === runId && path.includes(value.astronaut_id))))
  throw Error(`Unexpected request: ${url}`)
}

beforeEach(() => {
  runs = []; health = []; environment = []; postBehavior = null
  vi.stubGlobal('fetch', vi.fn(async (url, options) => respond(url, options)))
})

async function open() {
  render(<MemoryRouter initialEntries={['/demo']}><App /></MemoryRouter>)
  await screen.findByRole('form', { name: 'Simulation configuration' })
  await waitFor(() => expect(screen.getByRole('button', { name: 'Start simulation' })).toBeEnabled())
}

const posts = () => fetch.mock.calls.filter(([, options]) => options?.method === 'POST')

test('renders scenario options, fictional labels and empty sensor readings without generating data', async () => {
  await open()
  expect(screen.getByRole('heading', { name: 'Mission simulator' })).toBeInTheDocument()
  expect(screen.getByRole('combobox', { name: 'Scenario' }).options).toHaveLength(5)
  expect(screen.getAllByText('No data').length).toBeGreaterThanOrEqual(5)
  expect(screen.getAllByText('Simulated · Fictional')).toHaveLength(5)
  expect(screen.getByRole('button', { name: 'Advance one tick' })).toBeDisabled()
  expect(posts()).toHaveLength(0)
})

test('starts selected scenario and advances one explicit tick with units and timestamps', async () => {
  const user = userEvent.setup()
  await open()
  await user.selectOptions(screen.getByRole('combobox', { name: 'Scenario' }), 'environmental_change')
  await user.click(screen.getByRole('button', { name: 'Start simulation' }))
  await screen.findByText('Simulation created. Advance a tick to generate fictional readings.')
  await waitFor(() => expect(screen.getByRole('button', { name: 'Advance one tick' })).toBeEnabled())
  expect(JSON.parse(posts()[0][1].body).scenario).toBe('environmental_change')
  expect(JSON.parse(posts()[0][1].body).astronaut_id).toBe(crew[0].id)
  expect(health).toHaveLength(0)
  await user.click(screen.getByRole('button', { name: 'Advance one tick' }))
  await screen.findByText('One fictional tick saved successfully.')
  await waitFor(() => expect(screen.getByText('72')).toBeInTheDocument())
  expect(screen.getByText('800')).toBeInTheDocument()
  expect(screen.getByText('bpm')).toBeInTheDocument()
  expect(screen.getByText('ppm')).toBeInTheDocument()
  expect(screen.getByText('uSv/h')).toBeInTheDocument()
  expect(screen.getAllByText(/UTC$/).length).toBe(5)
  expect(JSON.parse(posts()[1][1].body)).toEqual({ steps: 1 })
  expect(posts()[1][1].headers['Idempotency-Key']).toMatch(/^[0-9a-f-]{36}$/)
})

test('refresh-style remount retrieves stored run and telemetry without advancing it', async () => {
  const user = userEvent.setup()
  await open()
  await user.click(screen.getByRole('button', { name: 'Start simulation' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Advance one tick' })).toBeEnabled())
  await user.click(screen.getByRole('button', { name: 'Advance one tick' }))
  await screen.findByText('72')
  const count = posts().length
  cleanup()
  render(<MemoryRouter initialEntries={['/demo']}><App /></MemoryRouter>)
  expect(await screen.findByText('72')).toBeInTheDocument()
  expect(posts()).toHaveLength(count)
  expect(runs[0].last_tick_index).toBe(0)
})

test('command failure can be retried with the same idempotency key', async () => {
  const user = userEvent.setup()
  let fail = true
  postBehavior = (path, body) => {
    if (fail) { fail = false; throw new TypeError('Offline') }
    return mutate(path, body)
  }
  await open()
  await user.click(screen.getByRole('button', { name: 'Start simulation' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Unable to reach the API')
  await user.click(screen.getByRole('button', { name: 'Retry same command' }))
  await screen.findByText('Simulation created. Advance a tick to generate fictional readings.')
  expect(posts()[0][1].headers['Idempotency-Key']).toBe(posts()[1][1].headers['Idempotency-Key'])
})

test('double clicks cannot start duplicate requests', async () => {
  let release
  postBehavior = (path, body) => new Promise(resolve => { release = () => resolve(mutate(path, body)) })
  const user = userEvent.setup()
  await open()
  await user.dblClick(screen.getByRole('button', { name: 'Start simulation' }))
  expect(posts()).toHaveLength(1)
  await act(async () => release())
  await screen.findByText('Simulation created. Advance a tick to generate fictional readings.')
})

test('switching astronaut clears old telemetry and exposes the global active-run conflict', async () => {
  const user = userEvent.setup()
  await open()
  await user.click(screen.getByRole('button', { name: 'Start simulation' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Advance one tick' })).toBeEnabled())
  await user.click(screen.getByRole('button', { name: 'Advance one tick' }))
  await screen.findByText('72')
  await user.selectOptions(screen.getByRole('combobox', { name: 'CREW PROFILE' }), crew[1].id)
  await screen.findByRole('heading', { name: crew[1].display_name })
  await screen.findByText(/An active run belongs to/)
  expect(screen.queryByText('72')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Start simulation' })).toBeDisabled()
})

test('API load failure is explicit and never replaced by mock sensor values', async () => {
  const previous = fetch
  vi.stubGlobal('fetch', vi.fn((url, options) => url.includes('/simulation/') ? Promise.reject(new TypeError('Offline')) : previous(url, options)))
  render(<MemoryRouter initialEntries={['/demo']}><App /></MemoryRouter>)
  expect(await screen.findByRole('alert')).toHaveTextContent('Unable to reach the API')
  expect(screen.queryByText('72')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Retry simulation load' })).toBeInTheDocument()
})

test('the original action button also reuses its key after a network failure', async () => {
  const user = userEvent.setup()
  let fail = true
  postBehavior = (path, body) => {
    if (fail) { fail = false; throw new TypeError('Lost response') }
    return mutate(path, body)
  }
  await open()
  await user.click(screen.getByRole('button', { name: 'Start simulation' }))
  await screen.findByRole('alert')
  await user.click(screen.getByRole('button', { name: 'Start simulation' }))
  await screen.findByText('Simulation created. Advance a tick to generate fictional readings.')
  expect(posts()[0][1].headers['Idempotency-Key']).toBe(posts()[1][1].headers['Idempotency-Key'])
})

test('delayed telemetry cannot appear after switching astronauts', async () => {
  const user = userEvent.setup()
  await open()
  await user.click(screen.getByRole('button', { name: 'Start simulation' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Advance one tick' })).toBeEnabled())
  let release
  const previous = fetch
  vi.stubGlobal('fetch', vi.fn((url, options) => url.includes(`/astronauts/${crew[0].id}/readings?`)
    ? new Promise(resolve => { release = () => resolve(ok(page([{ id: 'old', indicator: 'heart_rate', value: 999, unit: 'bpm', observed_at: '2026-11-15T12:00:00Z', tick_index: 0 }]))) })
    : previous(url, options)))
  await user.click(screen.getByRole('button', { name: 'Refresh saved state' }))
  await waitFor(() => expect(release).toBeTypeOf('function'))
  await user.selectOptions(screen.getByRole('combobox', { name: 'CREW PROFILE' }), crew[1].id)
  await screen.findByRole('heading', { name: crew[1].display_name })
  await act(async () => release())
  expect(screen.queryByText('999')).not.toBeInTheDocument()
})
