# TDAID Record — Authenticated API

The authenticated API follows Plan → Red → Green → Refactor → Validate.

## Plan

- Architecture and state-machine contract: [API_DESIGN.md](API_DESIGN.md)
- Business-readable acceptance contract: `tests/features/api_jobs.feature`
- Compatibility gate: all initial CLI and batch grading CLI tests remain green.
- Validation gate: unit, integration, Gherkin end-to-end, mutation, live HTTP,
  package, and dependency checks execute successfully.

## Red

Repository, worker, API, and Gherkin tests were introduced before production
modules. The first run stopped during collection with four expected import
errors for `api_models`, `repository`, `worker`, and `api`; no production
API module existed yet.

## Green

- Loop 1 implemented strict API models plus transactional SQLite jobs and audit
  events: 12 repository/model tests passed.
- Loop 2 implemented the background worker. Its first integration run exposed
  that Pydantic computed fields had been persisted into strict result models;
  canonical persistence was corrected to exclude computed presentation fields,
  then all 14 model/repository/worker tests passed.
- Loop 3 implemented fail-closed bearer authentication, lifespan management,
  routes, and the executable Gherkin contract: 23 API tests passed.
- The first complete compatibility gate passed all 60 tests that existed before
  mutation-driven hardening.

## Refactor

- Kept API request handlers limited to authentication, persistence, and worker
  notification; grading remains in `JobWorker`.
- Reused the CLI's configuration, discovery, selection, runner, grading, and
  report components rather than duplicating the domain pipeline.
- Documented the supported single-process topology after reviewing restart
  recovery semantics; distributed workers require leases rather than the service's
  unconditional interrupted-job recovery.
- Added focused lifecycle and propagation tests after mutation analysis showed
  that integration tests were too coarse around the thread boundary.
- Bumped the package and OpenAPI version to 0.3.0 and added local operations and
  security guidance.

## Validate

- Unit: 42 passed.
- Integration: 10 passed.
- Gherkin/HTTP end to end: 4 passed.
- Full regression: 67 passed.
- Mutation: 98 generated for `worker.py`; 97 killed, one detected by timeout,
  zero survived (98/98 detected).
- Live Uvicorn: Swagger UI loaded with all routes and no browser console errors;
  unauthenticated access returned `401`; a real local job progressed from
  `queued` to `succeeded`, returned two submissions and JSON/Markdown/CSV report
  paths, and emitted `job.created`, `job.started`, and `job.succeeded` events.
- Release checks: source and tests compiled, dependency consistency passed,
  `git diff --check` passed, package version reported 0.3.0, and
  `opengrader-0.3.0-py3-none-any.whl` built successfully.
