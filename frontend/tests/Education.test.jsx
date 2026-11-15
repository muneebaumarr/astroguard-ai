import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route, Outlet } from 'react-router'
import { beforeEach, expect, test, vi } from 'vitest'
import { api } from '../src/services/api'
import { Hazards } from '../src/pages/Hazards'
import { Guidance } from '../src/pages/Guidance'
import { guidanceSuggestions } from '../src/services/guidanceSuggestions'
import fixtures from '../../shared/fixtures/fictional.json'

const crew = fixtures.astronauts
const reference = { title: 'NASA: Five Hazards', url: 'https://www.nasa.gov/hrp/hazards/' }
const hazards = [
  ['space_radiation', 'Space Radiation'], ['isolation_confinement', 'Isolation and Confinement'],
  ['distance_from_earth', 'Distance from Earth'], ['gravity_fields', 'Gravity Fields'], ['hostile_closed_environments', 'Hostile and Closed Environments'],
].map(([slug, title]) => ({ slug, title, description: `Why it matters: Educational context for ${title}.\n\nCrew and operations: Research context.\n\nPreparedness concepts: Mission preparation.`,
  monitoring_limitations: 'Fictional telemetry cannot establish exposure or safety.', related_indicators: [], references: [reference] }))
const articles = [
  ['sleep_circadian', 'Sleep and circadian rhythm', 'isolation_confinement'],
  ['exercise_conditioning', 'Physical exercise and conditioning', 'gravity_fields'],
  ['hydration_nutrition', 'Hydration and nutrition', 'hostile_closed_environments'],
  ['crew_wellbeing', 'Crew mental wellbeing', 'isolation_confinement'],
  ['environmental_monitoring', 'Environmental monitoring and oxygen observations', 'hostile_closed_environments'],
  ['radiation_awareness', 'Radiation awareness', 'space_radiation'],
].map(([slug, title, hazard]) => ({ slug, title, hazard_slugs: [hazard], indicators: [],
  educational_text: 'Spaceflight context: General research education.\n\nEducational considerations: Learn what observations can and cannot establish.',
  limitations: 'Not individual medical advice or a validated intervention.', references: [reference], reviewed_on: '2026-11-15' }))

beforeEach(() => {
  vi.spyOn(api, 'hazards').mockResolvedValue(hazards)
  vi.spyOn(api, 'guidance').mockResolvedValue(articles)
  vi.spyOn(api, 'assessments').mockResolvedValue([])
  vi.spyOn(api, 'alerts').mockResolvedValue([])
  vi.spyOn(api, 'checkins').mockResolvedValue([])
  vi.spyOn(api, 'healthTelemetry').mockResolvedValue({ readings: [] })
})

function show(path = '/hazards', person = crew[0]) {
  const context = { selectedId: person?.id, profile: { status: person ? 'ready' : 'idle', astronaut: person } }
  return <MemoryRouter initialEntries={[path]}><Routes><Route element={<Outlet context={context} />}><Route path="/hazards" element={<Hazards />} /><Route path="/guidance" element={<Guidance />} /></Route></Routes></MemoryRouter>
}

test('all five hazards can be selected and show details, monitoring limits and official source links', async () => {
  const user = userEvent.setup()
  render(show())
  await screen.findByRole('region', { name: 'Space Radiation details' })
  for (const hazard of hazards) {
    const choice = screen.getByRole('button', { name: new RegExp(hazard.title) })
    await user.click(choice)
    expect(choice).toHaveAttribute('aria-pressed', 'true')
    const detail = screen.getByRole('region', { name: `${hazard.title} details` })
    expect(within(detail).getByRole('heading', { name: 'Preparedness concepts' })).toBeInTheDocument()
    expect(within(detail).getByText(hazard.monitoring_limitations)).toBeInTheDocument()
    expect(within(detail).getByRole('link', { name: /NASA: Five Hazards/ })).toHaveAttribute('href', reference.url)
  }
  expect(screen.getByText(/not NASA-approved or clinically validated/)).toBeInTheDocument()
})

test('hazard deep links, related-topic navigation and filtering use the existing pages', async () => {
  const user = userEvent.setup()
  render(show('/hazards?hazard=space_radiation'))
  await screen.findByRole('region', { name: 'Space Radiation details' })
  await user.click(screen.getByRole('link', { name: 'Explore related educational topics' }))
  expect(await screen.findByRole('heading', { name: 'Radiation awareness' })).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Hydration and nutrition' })).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Show all topics' }))
  expect(screen.getByRole('heading', { name: 'Hydration and nutrition' })).toBeInTheDocument()
})

test('guidance exposes all six educational topics, source references and limitations', async () => {
  const user = userEvent.setup()
  render(show('/guidance'))
  await screen.findByRole('heading', { name: 'Sleep and circadian rhythm' })
  for (const article of articles) expect(screen.getByRole('heading', { name: article.title })).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Read topic: Hydration and nutrition' }))
  expect(screen.getByText('Not individual medical advice or a validated intervention.')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: /NASA: Five Hazards/ })).toHaveAttribute('rel', 'noopener noreferrer')
  expect(screen.getByText(/Content reviewed 2026-11-15/)).toBeInTheDocument()
  expect(await screen.findByText(/No relevant recorded context/)).toBeInTheDocument()
})

test('missing crew records do not hide the general educational library', async () => {
  render(show('/guidance', null))
  expect(await screen.findByRole('heading', { name: 'Radiation awareness' })).toBeInTheDocument()
  expect(screen.getByText(/Select a loaded fictional crew profile/)).toBeInTheDocument()
  expect(api.checkins).not.toHaveBeenCalled()
})

test.each([
  ['/hazards', 'hazards', 'No hazard education is available.'],
  ['/guidance', 'guidance', 'No educational topics match this selection.'],
])('empty %s collection shows an honest empty state', async (path, method, message) => {
  api[method].mockResolvedValue([])
  render(show(path))
  expect(await screen.findByText(message)).toBeInTheDocument()
})

test.each([
  ['/hazards', 'hazards', 'Retry hazards', 'Space Radiation'],
  ['/guidance', 'guidance', 'Retry guidance', 'Radiation awareness'],
])('%s loading failure is explicit and retry restores API content', async (path, method, retry, title) => {
  api[method].mockRejectedValueOnce(new Error('Education service unavailable'))
  render(show(path))
  expect(await screen.findByRole('alert')).toHaveTextContent('Education service unavailable')
  await userEvent.setup().click(screen.getByRole('button', { name: retry }))
  expect((await screen.findAllByRole('heading', { name: title })).length).toBeGreaterThan(0)
})

test('context failure keeps general educational material available', async () => {
  api.alerts.mockRejectedValue(new Error('Context unavailable'))
  render(show('/guidance'))
  expect(await screen.findByRole('alert')).toHaveTextContent('Context unavailable')
  expect(screen.getByRole('heading', { name: 'Radiation awareness' })).toBeInTheDocument()
})

test('oxygen assessment evidence suggests environmental education with an explicit fictional reason', async () => {
  api.assessments.mockResolvedValue([{ id: 'own-assessment', astronaut_id: crew[0].id, evaluated_at: '2026-11-15T12:00:00Z', results: [{ rule_id: 'demo_oxygen', outcome: 'triggered',
    evidence: [{ indicator: 'spo2', value: 94, unit: '%', observed_at: '2026-11-15T11:59:00Z' }] }] }])
  render(show('/guidance'))
  const context = screen.getByRole('region', { name: 'Fictional topic suggestions' })
  expect(await within(context).findByText(/Fictional assessment considered spo2: 94 %/)).toBeInTheDocument()
  expect(within(context).getByRole('link', { name: 'Environmental monitoring and oxygen observations' })).toHaveAttribute('href', '/guidance?topic=environmental_monitoring')
  expect(within(context).queryByRole('link', { name: 'Radiation awareness' })).not.toBeInTheDocument()
})

test('suggestions isolate astronaut records and never infer radiation or gravity hazards from heart rate', () => {
  const result = guidanceSuggestions({ astronautId: crew[0].id, articles,
    checkins: [{ astronaut_id: crew[1].id, observed_at: '2026-11-15T12:00:00Z', sleep_hours: 2 }],
    assessments: [{ id: 'other', astronaut_id: crew[1].id, evaluated_at: '2026-11-15T12:00:00Z', results: [{ outcome: 'triggered', guidance_slugs: ['radiation_awareness'], evidence: [] }] }],
    alerts: [{ astronaut_id: crew[1].id, state: 'open', latest_assessment_id: 'other' }],
    readings: [{ astronaut_id: crew[0].id, indicator: 'heart_rate', value: 130 }, { astronaut_id: crew[1].id, indicator: 'radiation_dose_rate', value: 40 }] })
  expect(result).toEqual([])
})

test('zero-valued self-reports remain real context and unrelated missing fields are not fabricated', () => {
  const result = guidanceSuggestions({ astronautId: crew[0].id, articles, checkins: [{ astronaut_id: crew[0].id, observed_at: '2026-11-15T12:00:00Z', sleep_hours: 0, exercise_minutes: 0, mood: null }] })
  expect(result.map(item => item.slug)).toEqual(['sleep_circadian', 'exercise_conditioning'])
  expect(result[0].reasons[0]).toContain('0 h')
})

test('astronaut switching ignores delayed old context and never shows another crew member records', async () => {
  let release
  api.checkins.mockImplementationOnce(() => new Promise(resolve => { release = resolve }))
  const rendered = render(show('/guidance'))
  await waitFor(() => expect(release).toBeTypeOf('function'))
  rendered.rerender(show('/guidance', crew[1]))
  await screen.findByText(/No relevant recorded context/)
  await act(async () => release([{ astronaut_id: crew[0].id, observed_at: '2026-11-15T12:00:00Z', sleep_hours: 2 }]))
  const context = screen.getByRole('region', { name: 'Fictional topic suggestions' })
  expect(within(context).getByRole('heading')).toHaveTextContent(crew[1].display_name)
  expect(within(context).queryByText(/2 h/)).not.toBeInTheDocument()
})

test('unknown hazard and guidance selections have useful missing-content states', async () => {
  const rendered = render(show('/hazards?hazard=unknown'))
  expect(await screen.findByText(/This hazard category is unavailable/)).toBeInTheDocument()
  rendered.unmount()
  render(show('/guidance?topic=unknown'))
  expect(await screen.findByText(/The requested topic is unavailable/)).toBeInTheDocument()
})
