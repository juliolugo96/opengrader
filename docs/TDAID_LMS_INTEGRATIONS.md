# TDAID Record — LMS Integrations

## Think

The seam with the highest risk is not the Canvas HTTP call itself; it is proving
that only complete OpenGrader grades are sent, that external identifiers are
encoded safely, and that retries cannot duplicate an already delivered grade.
The design therefore separates strict domain contracts, a provider adapter,
durable link/delivery state, and orchestration.

## Describe

Acceptance behavior is captured in `tests/features/lms_integration.feature`.
The feature imports a Canvas assignment, retains an open local record and a
provider link, finalizes a PDF grade, synchronizes it with SIS identity
semantics, and proves replay idempotency.

## Assert (Red)

Unit tests were added first for identifier normalization, bounded percentages,
Canvas pagination and request encoding, repository uniqueness and delivery
idempotency. Integration, browser, and Gherkin scenarios cover the authenticated
API and instructor UI. These tests initially fail because the LMS modules and
routes do not exist.

## Implement (Green)

The green implementation introduced provider-neutral LMS contracts and an
adapter registry, a bounded same-origin Canvas REST adapter, durable SQLite
assignment links and delivery receipts, and an orchestration service that only
selects successful automated results or finalized PDF grades. Authenticated API
routes expose discovery, import, link, unlink, dry-run, and synchronized grade
delivery operations.

The localized instructor workspace now supports the complete Canvas workflow
without asking a professor to handle tokens or configuration files. The plans
workspace and edition documentation also distinguish shipped Community and
Hosted capabilities, available Canvas support, and explicitly planned Hosted
and Institution capabilities.

## Refactor and validate

Refactoring separated pure identifier and percentage logic into
`lms_contract.py`, allowing fast mutation testing without invoking network
transport. Boundary assertions were strengthened for blank/path-like IDs,
zero-score grades, a one-point maximum, exact validation failures, and half-up
rounding. React review moved stable empty-array fallbacks outside the page
component and retained direct typed form events.

Validation evidence:

- Python unit, integration, and Gherkin/e2e suite: 185 passed.
- Frontend component and API-client suite: 14 files, 57 tests passed.
- Browser Gherkin suite: 9 scenarios passed, including a live browser-to-API-to-
  SQLite persistence and audit journey.
- ESLint, strict TypeScript, and the Next.js production build passed.
- Independent browser verification loaded Plans, navigated to LMS integrations,
  found no error overlay, and recorded no console errors.
- Python mutation testing: 279 of 285 mutants killed (97.89%). Four surviving
  LMS mutations are behavior-equivalent Decimal formatting operations; the
  other two survivors are pre-existing dashboard rounding equivalents.
- Frontend mutation testing: 175 of 177 mutants killed (98.87%), with 100%
  mutation coverage for the LMS API-client surface. The two survivors are a
  pre-existing form-event call and an equivalent optional-chain removal for a
  closed locale union.
