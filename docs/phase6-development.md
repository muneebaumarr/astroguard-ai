# Phase 6: spaceflight hazards and educational guidance

The existing Guidance and Spaceflight Hazards routes are functional. No new dependencies,
shared DTO changes, repository signature changes or SQLite changes were needed.

## Features and source separation

Spaceflight Hazards offers five selectable cards with shareable query-string selection:
Space Radiation, Isolation and Confinement, Distance from Earth, Gravity Fields, and
Hostile and Closed Environments. Details explain why each matters, crew/operational
considerations, general preparedness concepts and monitoring limitations. Related-topic
links open the same Guidance page with a hazard filter.

Guidance contains six expandable articles: sleep/circadian rhythm, exercise/conditioning,
hydration/nutrition, crew mental wellbeing, environmental monitoring/oxygen observations,
and radiation awareness. Articles include limitations, external official sources, a fixed
content review date and links back to hazard categories. Both pages have loading, error,
retry, refresh, empty and unavailable-selection states and responsive aerospace styling.

The text is an AstroGuard-authored summary of general NASA educational information;
it is not an official NASA procedure, certification or endorsement. It is distinct from
fictional crew telemetry. No medications, personalized treatment, intake targets,
diagnoses, response procedures or agency-approved demo thresholds are supplied.

## Verified sources

Links were opened and verified during implementation on 2026-11-15. The fixed catalog
review date records this editorial review, not a NASA publication or endorsement date.

- [NASA five hazards overview](https://www.nasa.gov/hrp/hazards/)
- [Space Radiation](https://www.nasa.gov/hrp/hazard-space-radiation/)
- [Isolation and Confinement](https://www.nasa.gov/hrp/hazard-isolation-and-confinement/)
- [Distance from Earth](https://www.nasa.gov/hrp/hazard-distance-from-earth/)
- [Gravity Fields](https://www.nasa.gov/hrp/hazard-gravity-fields/)
- [Hostile/Closed Environments](https://www.nasa.gov/hrp/hazard-hostile-closed-environments/)
- [Inadequate Sleep and Irregular Schedules](https://www.nasa.gov/reference/risk-from-inadequate-sleep-and-irregular-schedules/)
- [Fundamentals of Human Health](https://www.nasa.gov/reference/fundamentals-of-human-health/)

Source links require internet when opened. Catalog API requests do not contact NASA or
any external service, so reading the installed app's education works offline locally.
The catalog is intentionally not a live literature feed and requires editorial updates.

## API and catalog architecture

All four added read-only routes already appear in the shared API contract:

| Method | Path under /api/v1 | Response |
|---|---|---|
| GET | /hazards | Page[Hazard] |
| GET | /hazards/{slug} | Hazard |
| GET | /guidance | Page[GuidanceArticle] |
| GET | /guidance/{slug} | GuidanceArticle |

Lists use existing limit/offset pagination. Guidance additionally supports indicator
and hazard filters, combined with AND. Indicators must be existing health/environment
enum values; sleep_hours is a check-in field, not a supported indicator query value.
Unknown hazard filters return an empty page. Missing detail slugs return the existing
404 not_found envelope. Invalid pagination/indicator values return 422.

Inspection found **no guidance or hazard repository in the shared UnitOfWork**. Adding
one would change the teammate integration boundary unnecessarily. Instead the service
holds a versioned fixed catalog of existing GuidanceArticle/Hazard DTOs and returns
fresh detached copies. There is no ORM model, new persistence interface or database
seed dependency. GET does not mutate any repository or generate observations.

## Fictional context suggestions

Shared contracts do not define personalized guidance records. The frontend therefore
labels these as educational topic suggestions, not saved recommendations. It loads
only the selected astronaut's assessment, alert, check-in and latest simulated health
telemetry endpoints. Records are also filtered by astronaut_id before use.

- Triggered rules in the latest assessment, plus assessments referenced by that crew's
  unresolved alerts, can suggest topics through explicit evidence indicator mappings or
  existing guidance_slugs that match available articles.
- Oxygen saturation and cabin CO2 evidence can point to environmental monitoring;
  radiation evidence can point to radiation awareness. These mappings suggest reading,
  not a cause, exposure estimate, diagnosis or confirmed hazard.
- Recorded sleep, stress/mood and exercise minutes suggest their directly related
  learning topics, including zero-valued entries. Presence of an observation, rather
  than a new frontend threshold, is the reason. Missing fields remain unknown.
- Heart rate alone does not infer gravity adaptation, dehydration, radiation exposure
  or isolation. Hydration/nutrition remains general education because intake is not
  recorded. Environmental context is taken from the selected astronaut's assessments;
  the guidance page does not load another crew member's telemetry or assessment.
- Every suggestion states why the topic appeared, with the considered value, unit and
  timestamp where available. Selecting a topic opens the existing library article.
- Crew changes abort requests and ignore delayed responses; failed personal-context
  loading leaves the public library available. Suggestions refresh explicitly and are
  not automatically treated as current medical recommendations.

Existing assessment details now link to the educational topic-suggestion page. No
Phase 5 rules, severity meanings, alert transitions or assessment write behavior changed.

## Files changed

- New `backend/app/services/education.py`: typed fixed catalog and source references.
- New `backend/app/api/v1/education.py`: four contract-defined GET routes.
- `backend/app/main.py`: router registration.
- New `backend/tests/test_education.py`: content, schema, pagination, filtering,
  error-envelope and read-only regressions.
- `backend/tests/test_api.py`: exact OpenAPI path assertion extended for the new routes.
- New `frontend/src/pages/Hazards.jsx` and `frontend/src/pages/Guidance.jsx`: interactive pages.
- New `frontend/src/hooks/useEducation.js`: abortable catalog loading and refresh.
- New `frontend/src/services/guidanceSuggestions.js`: explainable, astronaut-scoped suggestions.
- New `frontend/src/components/common/EducationContent.jsx`: source, text and disclaimer UI.
- `frontend/src/components/common/AssessmentDetails.jsx`: educational-context link.
- `frontend/src/app/App.jsx`, `frontend/src/app/navigation.js`: replace existing placeholders.
- `frontend/src/services/api.js`: education list/detail API calls.
- `frontend/src/styles/global.css`: responsive card, source and detail styles.
- New `frontend/tests/Education.test.jsx`: page interaction and context/isolation regressions.
- `frontend/tests/App.test.jsx`: functional education-route expectations and API mocks.
- `README.md`, `docs/phase6-development.md`: project status, source and demo documentation.

## Run and manual browser verification

Start one backend from the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Start frontend in another terminal:

```powershell
cd frontend
npm.cmd run dev
```

1. Open http://127.0.0.1:5173/hazards. Select each of the five cards; check details,
   preparedness concepts, monitoring limits and official source links.
2. Open Space Radiation's related topics. Confirm Guidance is filtered to radiation
   education. Show all topics and expand each of the six articles.
3. Save a fictional check-in with sleep/stress/mood/exercise observations on an unused
   UTC date. Open Guidance and verify the selected astronaut's suggestions explain the
   actual entry and timestamp, without a diagnosis or intervention claim.
4. Run fictional telemetry until an oxygen or cabin-related rule triggers. Open the
   assessment, follow its educational-context link and inspect the suggested reading.
5. Switch astronauts. Old personal explanations must disappear. The general catalog
   remains available for everyone. A crew member without relevant records gets an
   honest context empty state, not fabricated suggestions.
6. Follow an official source link and verify it opens separately. Source material is
   educational background and does not validate the fictional thresholds.
7. Use a narrow/mobile viewport. Cards and articles should stack without horizontal
   overflow. Refresh both pages; saved records remain while the backend process runs.

## Verification and limits

Run `python -m pytest shared/tests backend/tests -v` from root using the project venv,
then `npm.cmd test -- --run` and `npm.cmd run build` from frontend.
Automated UI tests use jsdom and mocked API data; they do not constitute a manual
browser walkthrough. Catalog tests make no network requests.

Final verification: **212 Python tests passed**, **83 frontend tests passed**, and
**production build passed**. Phase 6 adds 11 backend cases and 14 frontend cases.
Existing phase tests remain in place; exact navigation and OpenAPI assertions now
require the functional education pages and endpoints. The production main bundle
is approximately 700 kB minified / 208 kB gzipped, retaining the nonfatal size warning.

Known limits: short curated summaries, no live source updates or personalized guidance
storage, no clinical or operational decision authority, no true hazard detection,
no durable runtime storage until SQLite integration, and the existing Recharts-related
nonfatal production bundle-size warning. Separate Health History remains a placeholder.
