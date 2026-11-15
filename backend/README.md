# Backend foundation

Developer A owns API routes, services, memory adapter, simulation and assessments.
Depend on astroguard_contracts; inject repositories through its UnitOfWork.
Phase 1 provides a FastAPI app factory, six read-only /api/v1 endpoints and a
process-local memory adapter implementing every shared repository protocol.
The memory store loads the unchanged fictional fixtures and resets on restart.
Phase 2 adds atomic manual check-in submission/retrieval and limited educational
assessment retrieval. No simulator, clinical scoring engine or database routes are implemented.

Install the shared package first, then `pip install -e './backend[test]'` from
repository root. See ../docs/phase1-development.md for the complete PowerShell setup,
configuration, tests, startup commands and adapter behavior.
See ../docs/phase2-development.md for the current check-in workflow and API additions.
