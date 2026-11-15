import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, test, vi } from 'vitest'
import { App } from '../src/app/App'
import { validateCheckin, initialForm } from '../src/services/checkinForm'
import fictional from '../../shared/fixtures/fictional.json'

const astronauts = fictional.astronauts
const mission = fictional.missions[0]
const records = new Map()
const assessments = new Map()
const ok = data => ({ ok: true, status: 200, json: async () => data })
const page = items => ({ items, total: items.length, offset: 0, limit: 100 })
let postBehavior
let created

function makeResult(astronautId, body) {
  const checkin = { ...body, id: crypto.randomUUID(), created_at: body.observed_at, astronaut_id: astronautId,
    is_demo: true, sleep_hours: body.sleep_hours ?? null, mood: body.mood ?? null, stress: body.stress ?? null,
    exercise_minutes: body.exercise_minutes ?? null, notes: body.notes ?? null }
  const assessment = { id: crypto.randomUUID(), astronaut_id: astronautId, status: 'insufficient_data',
    results: [{ rule_id: 'clinical_context', explanation: 'Omitted observations remain unknown. Clinical evaluation is not implemented.',
      evidence: [{ record_id: checkin.id }] }] }
  const result = { checkin, readings: body.readings, assessment, alerts: [] }
  records.set(astronautId, [...(records.get(astronautId) || []), checkin])
  assessments.set(astronautId, [...(assessments.get(astronautId) || []), assessment])
  created = result
  return result
}

beforeEach(() => {
  records.clear()
  assessments.clear()
  created = null
  postBehavior = null
  vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
    const path = new URL(url).pathname
    if (path.endsWith('/health')) return ok({ status: 'ok', adapter: 'memory' })
    if (path === '/api/v1/missions') return ok(page([mission]))
    if (path === '/api/v1/astronauts') return ok(page(astronauts))
    if (path === `/api/v1/missions/${mission.id}`) return ok(mission)
    const person = astronauts.find(item => path.startsWith(`/api/v1/astronauts/${item.id}`))
    if (!person) throw Error(`Unexpected path ${path}`)
    const prefix = `/api/v1/astronauts/${person.id}`
    if (path === prefix) return ok(person)
    if (path === `${prefix}/checkins` && options.method === 'POST') {
      if (postBehavior) return postBehavior(person.id, JSON.parse(options.body), options)
      return ok(makeResult(person.id, JSON.parse(options.body)))
    }
    if (path === `${prefix}/checkins`) return ok(page(records.get(person.id) || []))
    if (path === `${prefix}/assessments`) return ok(page(assessments.get(person.id) || []))
    if (path.startsWith(`${prefix}/checkins/`)) return ok(records.get(person.id)?.find(item => path.endsWith(item.id)))
    throw Error(`Unexpected path ${path}`)
  }))
})

async function openForm() {
  render(<MemoryRouter initialEntries={['/check-in']}><App /></MemoryRouter>)
  return screen.findByRole('form', { name: 'Daily health check-in' })
}

const posts = () => fetch.mock.calls.filter(([, options]) => options?.method === 'POST')
const input = name => screen.getByLabelText(new RegExp(`^${name}`))

test('renders supported sections, units and explicit optional/required labels', async () => {
  const form = await openForm()
  for (const text of ['Vital signs', 'Sleep & wellness', 'Activity', 'Symptoms & notes']) expect(within(form).getByText(text)).toBeInTheDocument()
  expect(input('Check-in date')).toBeRequired()
  expect(input('Observation time')).toBeRequired()
  expect(input('Heart rate')).not.toBeRequired()
  expect(within(form).getByText('bpm')).toBeInTheDocument()
  expect(within(form).getAllByText('mmHg')).toHaveLength(2)
  expect(within(form).getByText('degC')).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: astronauts[0].display_name })).toBeInTheDocument()
})

test('requires an observation and validates the UTC date before posting', async () => {
  const user = userEvent.setup()
  await openForm()
  await user.click(screen.getByRole('button', { name: 'Save check-in' }))
  expect(screen.getByRole('alert')).toHaveTextContent('Record at least one')
  await user.clear(input('Check-in date'))
  await user.type(input('Additional notes'), 'Fictional observation')
  await user.click(screen.getByRole('button', { name: 'Save check-in' }))
  expect(screen.getByText('Choose a UTC check-in date.')).toBeInTheDocument()
  expect(posts()).toHaveLength(0)
})

test('validates blood pressure pairing and numeric ranges inline', async () => {
  const user = userEvent.setup()
  await openForm()
  await user.type(input('Systolic pressure'), '120')
  await user.type(input('Blood oxygen'), '101')
  await user.click(screen.getByRole('button', { name: 'Save check-in' }))
  expect(screen.getByText('Enter both blood pressure components.')).toBeInTheDocument()
  expect(screen.getByText('Enter a value from 0 to 100.')).toBeInTheDocument()
  expect(posts()).toHaveLength(0)
})

test('submits correct units and numeric types, displays saved result and refetches history', async () => {
  const user = userEvent.setup()
  await openForm()
  await screen.findByText('No check-ins yet')
  await user.type(input('Heart rate'), '72')
  await user.type(input('Sleep duration'), '0')
  await user.selectOptions(input('Mood'), '4')
  await user.type(input('Exercise activity'), '30')
  await user.type(input('Symptoms'), 'Fictional headache\nFictional fatigue')
  await user.click(screen.getByRole('button', { name: 'Save check-in' }))
  expect(await screen.findByText('Check-in saved successfully')).toBeInTheDocument()
  const [, options] = posts()[0]
  const body = JSON.parse(options.body)
  expect(body.readings).toEqual([{ indicator: 'heart_rate', value: 72, unit: 'bpm' }])
  expect(body.sleep_hours).toBe(0)
  expect(body.mood).toBe(4)
  expect(body.exercise_minutes).toBe(30)
  expect(body.symptoms).toEqual(['Fictional headache', 'Fictional fatigue'])
  expect(body.stress).toBeUndefined()
  expect(options.headers['Idempotency-Key']).toMatch(/^[0-9a-f-]{36}$/)
  const saved = screen.getByRole('region', { name: 'Saved check-in details' })
  expect(saved).toHaveTextContent('72 bpm')
  expect(saved).toHaveTextContent('0 h')
  expect(saved).toHaveTextContent('Insufficient information')
  expect(saved).toHaveTextContent('Clinical evaluation is not implemented')
  await waitFor(() => expect(screen.queryByText('No check-ins yet')).not.toBeInTheDocument())
  expect(screen.getByRole('button', { name: 'Saved' })).toBeDisabled()
})

test('network retry resends the identical payload and idempotency key', async () => {
  const user = userEvent.setup()
  let calls = 0
  postBehavior = (id, body) => {
    if (++calls === 1) throw new TypeError('Lost response')
    return ok(makeResult(id, body))
  }
  await openForm()
  await user.type(input('Additional notes'), 'Fictional retry')
  await user.click(screen.getByRole('button', { name: 'Save check-in' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Unable to reach the API')
  await user.click(screen.getByRole('button', { name: 'Retry / save check-in' }))
  await screen.findByText('Check-in saved successfully')
  expect(posts()).toHaveLength(2)
  expect(posts()[0][1].headers['Idempotency-Key']).toBe(posts()[1][1].headers['Idempotency-Key'])
  expect(posts()[0][1].body).toBe(posts()[1][1].body)
})

test('editing after failure creates a fresh command key', async () => {
  const user = userEvent.setup()
  postBehavior = () => { throw new TypeError('Offline') }
  await openForm()
  await user.type(input('Additional notes'), 'First observation')
  await user.click(screen.getByRole('button', { name: 'Save check-in' }))
  await screen.findByRole('alert')
  await user.type(input('Additional notes'), ' changed')
  await user.click(screen.getByRole('button', { name: 'Retry / save check-in' }))
  await waitFor(() => expect(posts()).toHaveLength(2))
  expect(posts()[0][1].headers['Idempotency-Key']).not.toBe(posts()[1][1].headers['Idempotency-Key'])
})

test('prevents double submission while a request is pending', async () => {
  let release
  postBehavior = (id, body) => new Promise(resolve => { release = () => resolve(ok(makeResult(id, body))) })
  const user = userEvent.setup()
  await openForm()
  await user.type(input('Heart rate'), '72')
  await user.dblClick(screen.getByRole('button', { name: 'Save check-in' }))
  expect(posts()).toHaveLength(1)
  expect(screen.getByRole('button', { name: 'Saving check-in…' })).toBeDisabled()
  await act(async () => release())
  expect(await screen.findByText('Check-in saved successfully')).toBeInTheDocument()
})

test('server validation details are shown beside the relevant input', async () => {
  postBehavior = () => ({ ok: false, status: 422, json: async () => ({ error: {
    message: 'Request validation failed', details: { 'body.readings.0.value': 'Example numeric validation error' }, code: 'validation_error',
  } }) })
  const user = userEvent.setup()
  await openForm()
  await user.type(input('Heart rate'), '72')
  await user.click(screen.getByRole('button', { name: 'Save check-in' }))
  expect(await screen.findByText('Example numeric validation error')).toBeInTheDocument()
  expect(input('Heart rate')).toHaveAttribute('aria-invalid', 'true')
})

test('history detail retrieval and a page reload use backend records', async () => {
  const result = makeResult(astronauts[0].id, { checkin_date: '2026-11-15', observed_at: '2026-11-15T12:00:00Z', context: 'resting', readings: [], symptoms: [], notes: 'Existing saved observation' })
  const user = userEvent.setup()
  const mounted = render(<MemoryRouter initialEntries={['/check-in']}><App /></MemoryRouter>)
  await user.click(await screen.findByRole('button', { name: /2026-11-15/ }))
  expect(await screen.findByRole('region', { name: 'Saved check-in details' })).toHaveTextContent('Existing saved observation')
  expect(fetch.mock.calls.some(([url]) => url.endsWith(`/checkins/${result.checkin.id}`))).toBe(true)
  mounted.unmount()
  await openForm()
  expect(await screen.findByRole('button', { name: /2026-11-15/ })).toBeInTheDocument()
})

test('switching astronauts clears records, form and success from the previous astronaut', async () => {
  makeResult(astronauts[0].id, { checkin_date: '2026-11-15', observed_at: '2026-11-15T12:00:00Z', context: 'resting', readings: [], symptoms: [], notes: 'Only Maya observation' })
  const user = userEvent.setup()
  await openForm()
  await user.click(await screen.findByRole('button', { name: /2026-11-15/ }))
  await screen.findByText('Only Maya observation')
  await user.type(input('Additional notes'), 'Unsubmitted Maya draft')
  await user.selectOptions(screen.getByRole('combobox', { name: 'CREW PROFILE' }), astronauts[1].id)
  await screen.findByRole('heading', { name: astronauts[1].display_name })
  expect(screen.queryByText('Only Maya observation')).not.toBeInTheDocument()
  expect(input('Additional notes')).toHaveValue('')
  expect(await screen.findByText('No check-ins yet')).toBeInTheDocument()
  expect(sessionStorage.getItem('astroguard.selectedAstronaut')).toBe(astronauts[1].id)
  cleanup()
  await openForm()
  expect(await screen.findByRole('heading', { name: astronauts[1].display_name })).toBeInTheDocument()
  expect(await screen.findByText('No check-ins yet')).toBeInTheDocument()
})

test('a completed old save response cannot appear under a newly selected astronaut', async () => {
  let release
  postBehavior = (id, body) => new Promise(resolve => { release = () => resolve(ok(makeResult(id, body))) })
  const user = userEvent.setup()
  await openForm()
  await user.type(input('Additional notes'), 'Pending Maya observation')
  await user.click(screen.getByRole('button', { name: 'Save check-in' }))
  await waitFor(() => expect(release).toBeTypeOf('function'))
  await user.selectOptions(screen.getByRole('combobox', { name: 'CREW PROFILE' }), astronauts[1].id)
  await screen.findByRole('heading', { name: astronauts[1].display_name })
  await act(async () => release())
  expect(screen.queryByText('Check-in saved successfully')).not.toBeInTheDocument()
  expect(screen.queryByRole('region', { name: 'Saved check-in details' })).not.toBeInTheDocument()
  expect(await screen.findByText('No check-ins yet')).toBeInTheDocument()
  expect(input('Additional notes')).toHaveValue('')
})

test('no astronaut profiles means no enabled submission form', async () => {
  const previous = fetch
  vi.stubGlobal('fetch', vi.fn((url, options) => url.includes('/astronauts?') ? Promise.resolve(ok(page([]))) : previous(url, options)))
  await render(<MemoryRouter initialEntries={['/check-in']}><App /></MemoryRouter>)
  expect(await screen.findByText('No crew profiles')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Save check-in' })).not.toBeInTheDocument()
})

test('validation accepts valid pressure pairs and rejects unsupported symptom sizes', () => {
  const form = { ...initialForm(), blood_pressure_systolic: '120', blood_pressure_diastolic: '80', symptoms: 'x'.repeat(101) }
  const result = validateCheckin(form)
  expect(result.errors.symptoms).toBeTruthy()
  expect(result.body.readings).toEqual([{ indicator: 'blood_pressure_systolic', value: 120, unit: 'mmHg' }, { indicator: 'blood_pressure_diastolic', value: 80, unit: 'mmHg' }])
})

test('a submitted check-in and its assessment are visible immediately after a refresh-style remount', async () => {
  const user = userEvent.setup()
  await openForm()
  await user.selectOptions(screen.getByRole('combobox', { name: 'CREW PROFILE' }), astronauts[1].id)
  await screen.findByRole('heading', { name: astronauts[1].display_name })
  await user.type(input('Additional notes'), 'Persisted Leo refresh regression')
  await user.click(screen.getByRole('button', { name: 'Save check-in' }))
  await screen.findByText('Check-in saved successfully')
  const savedId = created.checkin.id
  cleanup()
  await openForm()
  expect(await screen.findByRole('heading', { name: astronauts[1].display_name })).toBeInTheDocument()
  const detail = await screen.findByRole('region', { name: 'Saved check-in details' })
  expect(detail).toHaveTextContent('Persisted Leo refresh regression')
  expect(detail).toHaveTextContent('Clinical evaluation is not implemented')
  expect(records.get(astronauts[1].id)[0].id).toBe(savedId)
  const historyRequests = fetch.mock.calls.filter(([url]) => url.includes(`/astronauts/${astronauts[1].id}/checkins?`))
  expect(historyRequests.length).toBeGreaterThanOrEqual(2)
  expect(historyRequests.every(([url]) => !new URL(url).searchParams.has('from') && !new URL(url).searchParams.has('to'))).toBe(true)
})

test('a backdated saved record is restored instead of being hidden by the latest observation date', async () => {
  makeResult(astronauts[0].id, { checkin_date: '2026-11-15', observed_at: '2026-11-15T12:00:00Z', context: 'resting', readings: [], symptoms: [], notes: 'Newer observation' })
  const user = userEvent.setup()
  await openForm()
  fireEvent.change(input('Check-in date'), { target: { value: '2026-11-14' } })
  await user.type(input('Additional notes'), 'Backdated saved observation')
  await user.click(screen.getByRole('button', { name: 'Save check-in' }))
  await screen.findByText('Check-in saved successfully')
  cleanup()
  await openForm()
  expect(await screen.findByRole('region', { name: 'Saved check-in details' })).toHaveTextContent('Backdated saved observation')
  expect(screen.getByRole('button', { name: /2026-11-14/ })).toHaveAttribute('aria-pressed', 'true')
  expect(screen.getByRole('button', { name: /2026-11-15/ })).toBeInTheDocument()
})

test('remount restores only the selected astronaut records and permits reselection of the other crew member', async () => {
  for (const [index, person] of astronauts.entries()) {
    makeResult(person.id, { checkin_date: '2026-11-15', observed_at: '2026-11-15T12:00:00Z', context: 'resting', readings: [], symptoms: [], notes: `Crew ${index} saved observation` })
  }
  sessionStorage.setItem('astroguard.selectedAstronaut', astronauts[1].id)
  const user = userEvent.setup()
  await openForm()
  expect(await screen.findByRole('region', { name: 'Saved check-in details' })).toHaveTextContent('Crew 1 saved observation')
  expect(screen.queryByText('Crew 0 saved observation')).not.toBeInTheDocument()
  await user.selectOptions(screen.getByRole('combobox', { name: 'CREW PROFILE' }), astronauts[0].id)
  expect(await screen.findByRole('region', { name: 'Saved check-in details' })).toHaveTextContent('Crew 0 saved observation')
  expect(screen.queryByText('Crew 1 saved observation')).not.toBeInTheDocument()
})

test('a stale remembered record ID cannot fabricate a saved record after a backend reset', async () => {
  const result = makeResult(astronauts[0].id, { checkin_date: '2026-11-15', observed_at: '2026-11-15T12:00:00Z', context: 'resting', readings: [], symptoms: [], notes: 'Previous backend instance' })
  sessionStorage.setItem(`astroguard.selectedCheckin.${astronauts[0].id}`, result.checkin.id)
  await openForm()
  expect(await screen.findByRole('region', { name: 'Saved check-in details' })).toHaveTextContent('Previous backend instance')
  cleanup()
  records.clear()
  assessments.clear()
  await openForm()
  await screen.findByText('No check-ins yet')
  expect(screen.queryByRole('region', { name: 'Saved check-in details' })).not.toBeInTheDocument()
})
