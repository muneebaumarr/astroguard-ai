# Frontend foundation

Developer A owns this directory. Phase 1 implements the React/Vite/Tailwind shell,
eight routes, API-backed mission/crew selection, connection/retry/loading/empty states,
and an overview with unavailable measurements explicitly shown as No data.
The remaining feature pages are placeholders, not working monitoring features.

Run `npm ci`, then `npm run dev` from this directory. Copy .env.example to .env only
if overriding the default backend URL. `npm test` runs component/client tests;
`npm run build` produces an ignored dist directory. Recharts is installed for a
later phase; this foundation deliberately renders no fabricated chart data.

See ../docs/phase1-development.md for complete PowerShell instructions.
