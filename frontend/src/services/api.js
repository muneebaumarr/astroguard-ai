const baseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, status = 0, details = {}, code = '') {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
    this.code = code
  }
}

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${baseUrl}/api/v1${path}`, options)
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new ApiError('Unable to reach the API. Check that the backend is running, then retry.')
  }
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(data?.error?.message || `API request failed (${response.status}).`, response.status, data?.error?.details, data?.error?.code)
  if (data === null) throw new ApiError('The API returned an unreadable response.', response.status)
  return data
}

const get = (path, signal) => request(path, { signal })

async function collection(path, signal) {
  // Follow the agreed pagination contract rather than silently dropping later profiles.
  const items = []
  let offset = 0
  do {
    const page = await get(`${path}?limit=100&offset=${offset}`, signal)
    if (!Array.isArray(page.items) || !Number.isInteger(page.total) || page.total < 0) {
      throw new ApiError('The API returned an invalid collection.')
    }
    items.push(...page.items)
    offset += page.items.length
    if (offset >= page.total) return items
    if (!page.items.length) throw new ApiError('The API returned an incomplete collection.')
  } while (true)
}

export const api = {
  health: (signal) => get('/health', signal),
  missions: (signal) => collection('/missions', signal),
  mission: (id, signal) => get(`/missions/${encodeURIComponent(id)}`, signal),
  astronauts: (signal) => collection('/astronauts', signal),
  astronaut: (id, signal) => get(`/astronauts/${encodeURIComponent(id)}`, signal),
  checkins: (id, signal) => collection(`/astronauts/${encodeURIComponent(id)}/checkins`, signal),
  checkin: (id, checkinId, signal) => get(`/astronauts/${encodeURIComponent(id)}/checkins/${encodeURIComponent(checkinId)}`, signal),
  assessments: (id, signal) => collection(`/astronauts/${encodeURIComponent(id)}/assessments`, signal),
  createCheckin: (id, body, key, signal) => request(`/astronauts/${encodeURIComponent(id)}/checkins`, {
    method: 'POST', signal, headers: { 'Content-Type': 'application/json', 'Idempotency-Key': key }, body: JSON.stringify(body),
  }),
}
