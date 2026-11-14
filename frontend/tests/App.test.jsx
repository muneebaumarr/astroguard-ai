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
  expect(screen.getAllByText('No data')).toHaveLength(7)
  expect(screen.getByText('No assessment available')).toBeInTheDocument()
  expect(screen.getAllByText('Fictional demo').length).toBeGreaterThan(0)
  expect(screen.getByText(/All profiles are fictional/)).toBeInTheDocument()
  expect(fetch.mock.calls.some(([url]) => url.endsWith(`/astronauts/${astronauts[0].id}`))).toBe(true)
  expect(fetch.mock.calls.every(([url]) => !url.includes('/dashboard') && !url.includes('/readings'))).toBe(true)
})

test.each([
  ['Daily Check-In', 'Daily check-in'], ['Health History', 'Health history'],
  ['Assessments & Alerts', 'Assessments & alerts'], ['Guidance', 'Health guidance'],
  ['Spaceflight Hazards', 'Spaceflight hazards'], ['Demo Controls', 'Demo controls'],
])('navigation opens %s placeholder', async (label, heading) => {
  const user = userEvent.setup()
  renderApp()
  await user.click(within(screen.getByRole('navigation', { name: 'Main navigation' })).getByRole('link', { name: label }))
  expect(screen.getByRole('heading', { name: heading, level: 1 })).toBeInTheDocument()
  expect(screen.getByText('Workspace coming soon')).toBeInTheDocument()
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
