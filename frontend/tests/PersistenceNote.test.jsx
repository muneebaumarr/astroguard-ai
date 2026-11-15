import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import { PersistenceNote } from '../src/components/common/PersistenceNote'

test('SQLite persistence note explains that committed records survive backend restart', () => {
  render(<PersistenceNote adapter="sqlite" />)
  expect(screen.getByText(/committed records survive browser refresh and backend restarts/)).toBeInTheDocument()
  expect(screen.queryByText(/restarts clear memory/)).not.toBeInTheDocument()
})

test('memory persistence note retains the real limitation', () => {
  render(<PersistenceNote adapter="memory" />)
  expect(screen.getByText(/backend restarts clear memory/)).toBeInTheDocument()
})

test('unknown storage mode does not claim durable persistence', () => {
  render(<PersistenceNote />)
  expect(screen.getByText(/depends on the configured storage backend/)).toBeInTheDocument()
})
