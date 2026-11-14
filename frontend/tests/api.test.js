import { expect, test, vi } from 'vitest'
import { api } from '../src/services/api'

test('collection follows pagination rather than truncating profiles', async () => {
  vi.stubGlobal('fetch', vi.fn(async url => ({ ok: true, json: async () => ({
    items: [url.includes('offset=0') ? { id: 'first' } : { id: 'second' }], total: 2,
  }) })))
  expect(await api.astronauts()).toEqual([{ id: 'first' }, { id: 'second' }])
  expect(fetch).toHaveBeenCalledTimes(2)
})

test('incomplete collection fails explicitly', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => ({ items: [], total: 2 }) })))
  await expect(api.missions()).rejects.toThrow('incomplete collection')
})

test('aborted requests retain AbortError for effect cleanup', async () => {
  const error = new DOMException('Aborted', 'AbortError')
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(error))
  await expect(api.health(new AbortController().signal)).rejects.toBe(error)
})

test('invalid response is not replaced with local data', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => { throw Error('invalid JSON') } })))
  await expect(api.health()).rejects.toThrow('unreadable response')
})
