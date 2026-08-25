# TDAID Record — Professor Workspaces and Localization

## Plan

The increment is split into academic assignment contracts, persistent catalog
operations, generated grading definitions, PDF association, a professor-first
visual builder, localized navigation and workflows, and complete test layers.
Acceptance requires unit, integration, executable Gherkin, production browser,
and mutation tests.

## Red

Backend tests were written first for academic grouping, kind invariants,
persistence, filtering, generated definitions, launches, and PDF association.
The first run failed during collection because `opengrader.academic` did not
exist. Frontend tests were then introduced for the visual builder and the three
locale dictionaries; both failed because their modules did not exist. PDF
association received its own failing component test before the selector was
implemented.

## Green

The smallest complete vertical slice added:

- strict automated and written/PDF assignment contracts;
- SQLite CRUD, filters, audit events, and generated-definition storage;
- authenticated assignment CRUD and launch endpoints;
- optional PDF-to-assignment association and filtering;
- an academic catalog grouped by institution, course, period, and section;
- a guided builder with templates, evaluation checks, and collapsed advanced
  controls;
- edit, delete, automated launch, and written-work upload actions; and
- browser-local English, Spanish, and Simplified Chinese selection.

## Refactor

The visual model and execution engine remain separated: the browser sends a
typed academic definition, while the server alone materializes an engine file
when a job launches. Academic dimensions remain flexible strings to fit
different school systems. Translation is centralized in a typed context, the
document language follows the selected locale, and URL-based PDF preselection
uses a Suspense-safe App Router boundary.

## Validate

- Python unit, integration, and executable Gherkin suite: `166 passed`.
- React unit/integration suite: `50 passed`; lint and strict TypeScript checks
  passed.
- Production Next.js build and browser Gherkin suite: `6 passed`.
- Browser visual verification: the assignment route rendered meaningful
  content and navigation with no framework error overlay.
- Python mutation suite: `232/234` killed (`99.15%`); every new academic
  contract mutant was killed. The two survivors are equivalent pre-existing
  operations dashboard floating-point rounding mutations.
- Frontend mutation suite: `185/187` killed (`98.93%`), with complete mutation
  coverage for the new assignment and PDF-association API transport.
