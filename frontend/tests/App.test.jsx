import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, test, vi } from 'vitest'
import { App } from '../src/app/App'
import fictional from '../../shared/fixtures/fictional.json'

const astronauts = fictional.astronauts
const mission = fictional.missions[0]
const json = value => ({ ok: true, status: 200, json: async () => value })
const page = items => ({ items, total: items.length, limit: 100, offset: 0 })

function defaultResponse(url) {
  const path = new URL(url).pathname
  if (path === '/api/v1/hazards' || path === '/api/v1/guidance') return json(page([]))
  if (path.endsWith('/alerts') || path.endsWith('/readings') || path.endsWith('/environmental-readings') || path.endsWith('/checkins') || path.endsWith('/assessments') || path === '/api/v1/simulation/runs') return json(page([]))
  if (path === '/api/v1/simulation/scenarios') return json(page([{ scenario: 'routine', description: 'Fictional routine' }]))
  if (path.endsWith('/telemetry/latest')) return json({ readings: [], as_of: null })
  if (path.endsWith('/health')) return json({ status: 'ok', adapter: 'memory', contract_version: '0.1.0' })
  if (path === '/api/v1/missions') return json(page([mission]))
  if (path === '/api/v1/astronauts') return json(page(astronauts))
  if (path === `/api/v1/missions/${mission.id}`) return json(mission)
  const astronaut = astronauts.find(person => path === `/api/v1/astronauts/${person.id}`)
  if (astronaut) return json(astronaut)
  throw new Error(`Unexpected request: ${url}`)
}

beforeEach(() => vi.stubGlobal('fetch', vi.fn(async url => defaultResponse(url))))

function renderApp(path = '/') {
  return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)
}

test('renders API-backed profile, connection and honest empty health cards', async () => {
  renderApp()
  expect(await screen.findByRole('heading', { name: new RegExp(astronauts[0].display_name) })).toBeInTheDocument()
  expect(screen.getByText('API connected')).toBeInTheDocument()
  expect(screen.getAllByText('No data')).toHaveLength(5)
  expect(screen.getAllByText(/^No stored .* history\.$/)).toHaveLength(5)
  expect(screen.getByText('No assessment available')).toBeInTheDocument()
  expect(screen.getAllByText('Fictional demo').length).toBeGreaterThan(0)
  expect(screen.getByText(/All profiles are fictional/)).toBeInTheDocument()
  expect(fetch.mock.calls.some(([url]) => url.endsWith(`/astronauts/${astronauts[0].id}`))).toBe(true)
  await waitFor(() => expect(screen.getByRole('button', { name: 'Start simulation' })).toBeEnabled())
  expect(fetch.mock.calls.some(([url]) => url.includes(`/astronauts/${astronauts[0].id}/readings?source=simulated`))).toBe(true)
  expect(fetch.mock.calls.every(([url, options]) => !url.includes('/dashboard') && !options?.method)).toBe(true)
})

test('dashboard refetches saved fictional telemetry after refresh-style remount without generating readings', async () => {
  vi.stubGlobal('fetch', vi.fn(async url => {
    if (url.includes(`/astronauts/${astronauts[0].id}/telemetry/latest`)) return json({ readings: [{ indicator: 'heart_rate', value: 73.25, unit: 'bpm', observed_at: '2026-01-01T00:01:00Z' }] })
    if (url.includes('/missions/') && url.endsWith('/telemetry/latest')) return json({ readings: [{ indicator: 'cabin_co2', value: 812, unit: 'ppm', observed_at: '2026-01-01T00:01:00Z' }] })
    return defaultResponse(url)
  }))
  const first = renderApp()
  expect(await screen.findByText('73.25')).toBeInTheDocument()
  expect(screen.getByText('812')).toBeInTheDocument()
  first.unmount()
  renderApp()
  expect(await screen.findByText('73.25')).toBeInTheDocument()
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Refresh telemetry' }))
  expect(await screen.findByText('73.25')).toBeInTheDocument()
  await user.selectOptions(screen.getByRole('combobox', { name: 'CREW PROFILE' }), astronauts[1].id)
  await screen.findByRole('heading', { name: new RegExp(astronauts[1].display_name) })
  await waitFor(() => expect(screen.queryByText('Loading saved telemetry…')).not.toBeInTheDocument())
  expect(screen.queryByText('73.25')).not.toBeInTheDocument()
  expect(screen.getByText('812')).toBeInTheDocument()
  expect(fetch.mock.calls.every(([, options]) => !options?.method || options.method === 'GET')).toBe(true)
})

test('dashboard exposes telemetry failures and retries with its refresh control', async () => {
  let fail = true
  vi.stubGlobal('fetch', vi.fn(async url => {
    if (fail && url.endsWith('/telemetry/latest')) throw new Error('Offline')
    return defaultResponse(url)
  }))
  renderApp()
  expect(await screen.findByRole('alert')).toHaveTextContent('Unable to reach the API')
  fail = false
  await userEvent.setup().click(screen.getByRole('button', { name: 'Refresh telemetry' }))
  await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
  expect(screen.getByRole('link', { name: 'Open Mission Simulator' })).toHaveAttribute('href', '/demo')
})

test.each([
  ['Daily Check-In', 'Daily check-in'], ['Health History', 'Health history'],
  ['Assessments & Alerts', 'Assessments & alerts'], ['Guidance', 'Health guidance'],
  ['Spaceflight Hazards', 'Spaceflight hazards'], ['Mission Simulator', 'Mission simulator'],
])('navigation opens %s workspace', async (label, heading) => {
  const user = userEvent.setup()
  renderApp()
  await user.click(within(screen.getByRole('navigation', { name: 'Main navigation' })).getByRole('link', { name: label }))
  expect(screen.getByRole('heading', { name: heading, level: 1 })).toBeInTheDocument()
  if (label === 'Daily Check-In') {
    expect(await screen.findByRole('form', { name: 'Daily health check-in' })).toBeInTheDocument()
  } else if (label === 'Mission Simulator') {
    expect(await screen.findByRole('form', { name: 'Simulation configuration' })).toBeInTheDocument()
  } else if (label === 'Assessments & Alerts') {
    expect(await screen.findByRole('heading', { name: 'Latest assessment' })).toBeInTheDocument()
    expect(await screen.findByText('No assessments recorded.')).toBeInTheDocument()
  } else if (label === 'Guidance') {
    expect(await screen.findByText('No educational topics match this selection.')).toBeInTheDocument()
  } else if (label === 'Spaceflight Hazards') {
    expect(await screen.findByText('No hazard education is available.')).toBeInTheDocument()
  } else expect(screen.getByText('Workspace coming soon')).toBeInTheDocument()
})

test('selecting another astronaut fetches details and updates profile', async () => {
  const user = userEvent.setup()
  renderApp()
  await screen.findByRole('heading', { name: new RegExp(astronauts[0].display_name) })
  await user.selectOptions(screen.getByRole('combobox', { name: 'CREW PROFILE' }), astronauts[1].id)
  expect(await screen.findByRole('heading', { name: new RegExp(astronauts[1].display_name) })).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: new RegExp(astronauts[0].display_name) })).not.toBeInTheDocument()
  expect(fetch.mock.calls.some(([url]) => url.endsWith(`/astronauts/${astronauts[1].id}`))).toBe(true)
})

test('orbital view keeps NASA imagery illustrative and crew cards switch the API-backed profile', async () => {
  const user = userEvent.setup()
  renderApp()
  await screen.findByRole('heading', { name: new RegExp(astronauts[0].display_name) })
  const stage = screen.getByRole('region', { name: 'Orbital telemetry view' })
  expect(stage.querySelector('img')).toHaveAttribute('src', '/images/spacewalk.jpg')
  expect(stage.querySelector('img')).toHaveAttribute('alt', '')
  expect(within(stage).getByRole('link', { name: /Background: NASA/ })).toHaveAttribute('href', 'https://www.nasa.gov/image-article/astronaut-frank-rubio-installs-roll-out-solar-array-during-spacewalk/')
  await user.click(within(stage).getByRole('button', { name: `Select ${astronauts[1].display_name} crew profile` }))
  expect(await screen.findByRole('heading', { name: new RegExp(astronauts[1].display_name) })).toBeInTheDocument()
  expect(screen.getByRole('combobox', { name: 'CREW PROFILE' })).toHaveValue(astronauts[1].id)
  expect(screen.getByRole('button', { name: `Select ${astronauts[1].display_name} crew profile` })).toHaveAttribute('aria-pressed', 'true')
})

test('a delayed old response cannot replace the newly selected profile or mission', async () => {
  let releaseFirst
  const otherMission = { ...mission, id: '175f7daa-ae9d-4b54-ae07-5ade216214d1', name: 'Second Fictional Mission' }
  vi.stubGlobal('fetch', vi.fn(async url => {
    if (url.endsWith(`/astronauts/${astronauts[0].id}`)) return new Promise(resolve => { releaseFirst = resolve })
    if (url.endsWith(`/astronauts/${astronauts[1].id}`)) return json({ ...astronauts[1], mission_id: otherMission.id })
    if (url.endsWith(`/missions/${otherMission.id}`)) return json(otherMission)
    return defaultResponse(url)
  }))
  const user = userEvent.setup()
  renderApp()
  await waitFor(() => expect(releaseFirst).toBeTypeOf('function'))
  await user.selectOptions(screen.getByRole('combobox', { name: 'CREW PROFILE' }), astronauts[1].id)
  await screen.findByRole('heading', { name: new RegExp(astronauts[1].display_name) })
  await act(async () => { releaseFirst(json(astronauts[0])) })
  expect(screen.getByRole('heading', { name: new RegExp(astronauts[1].display_name) })).toBeInTheDocument()
  expect(screen.getAllByText(otherMission.name).length).toBeGreaterThan(0)
})

test('API failure displays retry and never substitutes mock profiles', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
  const user = userEvent.setup()
  renderApp()
  expect(await screen.findByRole('alert')).toHaveTextContent('Unable to reach the API')
  expect(screen.getByText('API unavailable')).toBeInTheDocument()
  expect(screen.queryByText(astronauts[0].display_name)).not.toBeInTheDocument()
  vi.stubGlobal('fetch', vi.fn(async url => defaultResponse(url)))
  await user.click(screen.getByRole('button', { name: 'Retry connection' }))
  expect(await screen.findByRole('heading', { name: new RegExp(astronauts[0].display_name) })).toBeInTheDocument()
})

test('an empty API collection displays an explicit empty state', async () => {
  vi.stubGlobal('fetch', vi.fn(async url => url.includes('/astronauts?') ? json(page([])) : defaultResponse(url)))
  renderApp()
  expect(await screen.findByRole('heading', { name: 'No crew profiles' })).toBeInTheDocument()
  expect(screen.getByRole('combobox')).toBeDisabled()
})

test('loading remains visible until responses arrive', async () => {
  vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
  renderApp()
  expect(screen.getByText('Loading mission data…')).toBeInTheDocument()
  expect(screen.getByText('Connecting')).toBeInTheDocument()
})

test('mission page shows fictional crew and supports profile selection', async () => {
  const user = userEvent.setup()
  renderApp('/mission')
  await screen.findByRole('region', { name: 'Crew profiles' })
  expect(screen.getByRole('heading', { name: mission.name })).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Select profile' }))
  await waitFor(() => expect(screen.getByRole('combobox')).toHaveValue(astronauts[1].id))
  expect(await screen.findByRole('button', { name: 'Selected profile' })).toBeInTheDocument()
})

test('unknown URL has a recoverable not-found page', () => {
  renderApp('/unknown')
  expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Return to overview' })).toBeInTheDocument()
})

test('profile detail failure is visible without claiming measurements are available', async () => {
  vi.stubGlobal('fetch', vi.fn(async url => url.endsWith(`/astronauts/${astronauts[0].id}`)
    ? { ok: false, status: 404, json: async () => ({ error: { message: 'Astronaut not found' } }) }
    : defaultResponse(url)))
  renderApp()
  expect(await screen.findByRole('alert')).toHaveTextContent('Astronaut not found')
  expect(screen.queryByText('Mission context connected')).not.toBeInTheDocument()
})
