import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route, Outlet } from 'react-router'
import { beforeEach, expect, test, vi } from 'vitest'
import { api } from '../src/services/api'
import { Assessments } from '../src/pages/Assessments'
import fixtures from '../../shared/fixtures/fictional.json'

const crew = fixtures.astronauts, mission = fixtures.missions[0]
const assessment = { id: 'd7b44626-099d-4073-8fbd-88c8b952a87d', astronaut_id: crew[0].id, evaluated_at: '2026-11-15T12:00:00Z',
  status: 'crew_medical_review', ruleset_version: 'educational-demo-v2', results: [{ rule_id: 'demo_heart_rate', outcome: 'triggered',
    workflow_status: 'crew_medical_review', explanation: 'Fictional demo heart rate exceeds the authored elevated review boundary. Not a clinical threshold.',
    evidence: [{ record_id: 'reading-one', record_type: 'health_reading', observed_at: '2026-11-15T11:59:00Z', indicator: 'heart_rate', value: 130, unit: 'bpm' }], missing_data: [] }] }
const alert = { id: 'bbc62050-e373-4cd9-820f-ec2ece806981', astronaut_id: crew[0].id, rule_id: 'demo_heart_rate', workflow_status: 'crew_medical_review',
  state: 'open', first_assessment_id: assessment.id, latest_assessment_id: assessment.id, opened_at: assessment.evaluated_at }
let storedAssessments, storedAlerts

beforeEach(() => {
  storedAssessments = [structuredClone(assessment)]; storedAlerts = [structuredClone(alert)]
  vi.spyOn(api, 'assessments').mockImplementation(async id => structuredClone(storedAssessments.filter(value => value.astronaut_id === id)))
  vi.spyOn(api, 'alerts').mockImplementation(async id => structuredClone(storedAlerts.filter(value => value.astronaut_id === id)))
  vi.spyOn(api, 'assessmentCommand').mockImplementation(async (id, operation, alertId) => {
    if (operation === 'evaluate') return structuredClone(assessment)
    const found = storedAlerts.find(value => value.id === alertId)
    found.state = 'acknowledged'; found.acknowledged_at = '2026-11-15T12:01:00Z'
    return structuredClone(found)
  })
})

function show(person = crew[0], path = '/assessments') {
  const context = { status: 'ready', selectedId: person.id, astronauts: crew, profile: { status: 'ready', astronaut: person, mission } }
  return <MemoryRouter initialEntries={[path]}><Routes><Route element={<Outlet context={context} />}><Route path="/assessments" element={<Assessments />} /></Route></Routes></MemoryRouter>
}

test('renders assessment reasoning, supporting values, timestamps, exact review labels and educational disclaimer', async () => {
  render(show())
  expect(await screen.findByText('heart rate: 130 bpm')).toBeInTheDocument()
  expect(screen.getByText(/2026-11-15T11:59:00Z/)).toBeInTheDocument()
  expect(screen.getAllByText('crew medical review').length).toBeGreaterThanOrEqual(2)
  expect(screen.getAllByText(/Not a clinical threshold/)).toHaveLength(2)
  expect(screen.getAllByText(/not NASA-approved medical standards/).length).toBeGreaterThan(0)
  const alerts = screen.getByRole('region', { name: 'Recent alerts' })
  expect(within(alerts).getByRole('link', { name: 'Supporting assessment' })).toHaveAttribute('href', `/assessments?assessment=${assessment.id}`)
  expect(api.assessmentCommand).not.toHaveBeenCalled()
})

test('empty API data has honest assessment and alert empty states', async () => {
  storedAssessments = []; storedAlerts = []
  render(show())
  expect(await screen.findByText('No assessments recorded.')).toBeInTheDocument()
  expect(screen.getByText(/No assessment available/)).toBeInTheDocument()
  expect(screen.getByText(/No alerts recorded/)).toBeInTheDocument()
})

test('load failure is visible and refresh recovers', async () => {
  api.alerts.mockRejectedValueOnce(new Error('Alert service unavailable'))
  render(show())
  expect(await screen.findByRole('alert')).toHaveTextContent('Alert service unavailable')
  await userEvent.setup().click(screen.getByRole('button', { name: 'Refresh assessments' }))
  expect(await screen.findByText('heart rate: 130 bpm')).toBeInTheDocument()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})

test('acknowledgement uses API, updates lifecycle and preserves supporting assessment', async () => {
  const user = userEvent.setup()
  render(show())
  await user.click(await screen.findByRole('button', { name: 'Acknowledge alert' }))
  await waitFor(() => expect(screen.queryByRole('button', { name: 'Acknowledge alert' })).not.toBeInTheDocument())
  expect(screen.getByText(/Acknowledged 2026-11-15T12:01:00Z/)).toBeInTheDocument()
  expect(api.assessmentCommand.mock.calls[0].slice(0, 3)).toEqual([crew[0].id, 'acknowledge', alert.id])
  expect(screen.getByText('heart rate: 130 bpm')).toBeInTheDocument()
})

test('evaluate and network retry reuse the same command UUID', async () => {
  api.assessmentCommand.mockRejectedValueOnce(new Error('Lost response'))
  const user = userEvent.setup()
  render(show())
  await screen.findByText('heart rate: 130 bpm')
  await user.click(screen.getByRole('button', { name: 'Evaluate stored observations' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Lost response')
  await user.click(screen.getByRole('button', { name: 'Retry same command' }))
  await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
  expect(api.assessmentCommand).toHaveBeenCalledTimes(2)
  expect(api.assessmentCommand.mock.calls[0][3]).toMatch(/^[0-9a-f-]{36}$/)
  expect(api.assessmentCommand.mock.calls[1][3]).toBe(api.assessmentCommand.mock.calls[0][3])
})

test('switching astronauts clears previous assessments and alerts, including delayed responses', async () => {
  let release
  api.assessments.mockImplementationOnce(() => new Promise(resolve => { release = resolve }))
  const rendered = render(show())
  await waitFor(() => expect(release).toBeTypeOf('function'))
  rendered.rerender(show(crew[1]))
  await screen.findByText('No assessments recorded.')
  await act(async () => release([assessment]))
  expect(screen.queryByText('heart rate: 130 bpm')).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Acknowledge alert' })).not.toBeInTheDocument()
  expect(screen.getByText(/No alerts recorded/)).toBeInTheDocument()
})

test('linked assessment from another astronaut cannot leak into the selected workspace', async () => {
  render(show(crew[1], `/assessments?assessment=${assessment.id}`))
  expect(await screen.findByText(/This assessment is unavailable for the selected astronaut/)).toBeInTheDocument()
  expect(screen.queryByText('heart rate: 130 bpm')).not.toBeInTheDocument()
})

test('both supported review priorities are displayed without invented severity names', async () => {
  storedAlerts.push({ ...alert, id: 'another-alert', workflow_status: 'review_suggested', state: 'acknowledged', acknowledged_at: '2026-11-15T12:01:00Z' })
  render(show())
  expect(await screen.findByText('review suggested')).toBeInTheDocument()
  expect(screen.getAllByText('crew medical review').length).toBeGreaterThan(0)
})
