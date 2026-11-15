# Phase 2 refresh persistence investigation

## Reproduction and root causes

The existing API was inspected before application changes. Its startup command was
`python -m uvicorn app.main:app --reload --port 8000`. Both Maya's and Leo's November
15 check-ins were returned by the API. Chrome's accessibility tree showed Leo's
November 15 entry in Previous check-ins before and after browser refresh, still
under Leo's restored profile. Thus browser-only record deletion was not reproduced.

A new fictional check-in survived six independent live detail/history GET requests
under worker PID 6676; the other astronaut's history correctly excluded it. No date
filters were sent. Two distinct problems/mechanisms were then reproduced:

1. **Frontend display gap:** a new regression test saved a record, remounted the
   frontend, and failed because Saved check-in details was missing. History loaded,
   but `saved` initialized to null and was populated only by POST success or a history
   click. Initial history loading did not restore the panel, which was below the form.
2. **True memory reset through development reload:** saving Python regression tests
   caused worker PID 6676 to exit. The next API history contained only November 7–13
   fixtures. This reproduced actual record loss through the running --reload watcher.
   It demonstrates the environment's reset mechanism, not proof of the exact timing
   of the user's earlier incident. A browser refresh alone did not erase the records.

No per-request store or commit defect was found. MemoryAdapterFactory is created once
in application lifespan and reused from app.state.adapter. New UnitOfWork snapshots
read that same factory; POST commits before responding. Frontend history requests use
pagination, not date/from/to filters. Reload or another backend process has independent
memory; an HTTP 200 alone says nothing about whether a particular ID is in its body.

## Fix and changed files

- `frontend/src/pages/DailyCheckin.jsx`: restore last-viewed record from fetched history,
  remember only its per-astronaut ID, safely fall back to latest/empty, and place saved
  details above the form. Backend data remains authoritative.
- `frontend/src/styles/global.css`: spacing for the restored detail panel.
- `frontend/tests/Checkin.test.jsx`: refresh, backdated entry, astronaut isolation and
  stale-ID regression tests. The refresh test failed before the source fix.
- `backend/tests/test_checkins.py`: real application POST/separate GET lifecycle and
  independent UnitOfWork sharing regressions.
- `docs/phase2-development.md`: restoration behavior and no-reload verification guidance.
- `docs/refresh-persistence-investigation.md`: this evidence and report.

No shared contract, API shape, backend adapter/lifespan logic, database module or
SQLite work changed. Existing tests were retained.

## Final verification

- `.venv/Scripts/python.exe -m pytest shared/tests backend/tests -v`: 153 passed
  (79 shared, 74 backend), including both new backend lifecycle regressions.
- `npm test -- --run`: 36 passed, including four new refresh/isolation regressions.
- `npm run build`: passed.
- `python -m pip check`: no broken requirements.
- `git diff --check`: passed; shared/ and database/ are unchanged.
- The original submitted-record/remount test failed before the frontend fix and
  passed after it. Live separate-request persistence was verified before changes.
- No commits, pushes or merges were performed. Existing user-started servers were
  not stopped; their --reload worker did restart when Python test edits were saved.

## Manual verification

Use a single backend process without reload from repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start Vite in another terminal (`cd frontend`, then `npm.cmd run dev`). Open
http://127.0.0.1:5173/check-in. Select an astronaut, submit on an unused UTC date,
then refresh. Its date must remain listed and its saved values/assessment should
open above the form. Switch astronauts and back, then refresh again. Check a
backdated observation too; there is no implicit current-date filter.

Do not restart the backend during the check. If using --reload, watch for shutdown,
startup, `Started server process` or reload messages. Editing Python source/tests can
clear memory. Restart loss remains expected until the teammate's durable database
adapter is integrated. No persistence across process restarts is promised by this fix.
