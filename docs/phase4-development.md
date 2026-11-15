# Phase 4: Overview mission control

Overview now shows selected fictional crew/mission context, five API-backed sensor
cards with SVG sparklines, responsive Recharts area charts, latest check-in, latest
educational assessment and recent telemetry activity. Health and mission cabin
readings remain separate. Temperature uses °C on screen (the API unit remains degC).
No random frontend values, diagnoses or medical safety thresholds are used.

## Playback and existing API

No backend endpoint, DTO, repository, shared contract or database changes were needed.
The existing API prefix remains `/api/v1`. Overview reads scenarios, runs, latest
telemetry, paginated simulated astronaut reading history, mission environmental
history, check-ins and assessments. Saved records load without creating or advancing
a simulation. When present, history for the selected astronaut's active/latest run
is preferred; otherwise saved history remains visible. Cabin observations belong
to the mission and may be visible for other astronauts in that mission.

Start creates a paused run (seed 42, current UTC simulation start, 60 simulated seconds
per tick). Play is a **frontend playback state**, separate from backend run status.
Existing `/simulation/runs/{id}/steps` requires a paused backend run, so Overview
keeps it paused and posts `{ "steps": 1 }` about every two seconds. A legacy running
run is paused through the existing endpoint before its next explicit step. Each
request waits for the mutation and data reload before scheduling another timeout.
There are no overlapping ticks, duplicate timers or GET side effects.

Pause cancels the next timeout immediately. An already accepted in-flight tick may
still commit and appear; it cannot be undone by browser cancellation. Crew/mission
changes and unmount abort requests and cancel playback. Refresh also pauses playback.
Remount restores saved readings but never automatically resumes playback.

Every mutation has a UUID idempotency key. An unknown mutation result can be retried
with the same payload/key using **Retry same command**. Acknowledged mutations followed
by failed reads are repaired with Refresh telemetry, without repeating the mutation.
Errors stop automatic playback and remain visible. No reset API exists; Stop run
releases the global active-run slot and allows a new scenario without deleting history.

## Run locally (PowerShell)

From repository root, in one terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm.cmd run dev
```

Open http://127.0.0.1:5173/ . Keep the same backend process running during persistence
checks. Avoid a development reloader during this demo because a server restart clears memory.

## Manual browser checks

1. Open Overview. Confirm the selected astronaut, mission and SIMULATED DATA label.
2. If a seeded run belongs to another astronaut, select the named crew profile in
   the header and Stop run on Overview. Then select your desired astronaut.
3. Select a scenario and Start simulation. Confirm Play and Advance one tick enable.
4. Click Play. Watch readings, timestamps, tick count, sparklines and all five charts
   update about every two seconds. Each tick adds three health and two cabin readings.
5. Pause. Wait at least five seconds; no new ticks should appear. Advance one tick
   and confirm one additional tick, followed by no further automatic updates.
6. Refresh the browser. Readings/history must remain, with playback paused. Confirm
   check-in and educational assessment summaries if that crew has saved records.
7. Play and change astronauts. The former astronaut's readings must disappear and
   playback must stop. Return to the original astronaut to retrieve its saved history.
8. While playing, stop the backend. Confirm a visible error and stopped playback;
   restart and refresh. A reset backend has only seeded fixtures, not prior runtime data.
9. Resize to a narrow mobile viewport; cards, controls and charts should stack without
   horizontal page overflow. Reduced-motion preferences disable decorative animations.

## Verification and limitations

Run from root: `python -m pytest shared/tests backend/tests -v` using the project venv.
Run from frontend: `npm.cmd test -- --run` and `npm.cmd run build`.
Automated dashboard tests exercise actual Recharts rendering with measured jsdom
containers and mocked API responses; they do not constitute a manual browser walkthrough.

Verified results: 177 shared/backend tests passed, 60 frontend tests passed (including
13 new dashboard regressions), and production build passed. Vite reports a nonfatal
large-chunk warning: the main JavaScript bundle including Recharts is approximately
681 kB minified / 203 kB gzipped. Existing test assertions were retained or updated
to require the new five-sensor dashboard and historical chart empty states.

Memory persists only within one backend process. Only one paused/running run exists
globally. Playback is intentionally tab-local and stops on navigation; background-tab
timer throttling and network latency may slow it. Separate browser tabs are not
coordinated and should not both play the same run. Latest 120 observations per sensor
are charted; paginated history is currently reloaded each tick for this deadline-focused
demo. Dedicated historical exploration, clinical rules and durable SQLite integration
remain outside Phase 4. Recharts increases the production JavaScript bundle size.
