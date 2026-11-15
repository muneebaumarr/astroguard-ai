import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: 'jsdom',
    setupFiles: './tests/setup.js',
    restoreMocks: true,
    clearMocks: true,
    // Keep jsdom workers within this laptop's capacity; excessive parallelism
    // caused five-second interaction tests to time out during full-suite runs.
    maxWorkers: 2,
  },
})
