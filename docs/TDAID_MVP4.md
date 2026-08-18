# TDAID Record — MVP 4 Operations Dashboard

## Plan

The increment is divided into a typed API client, browser-local settings,
same-origin proxy, reusable interface primitives, job and audit workspaces,
student-level result presentation, and API compatibility rules. Acceptance
requires unit, proxy integration, executable Gherkin browser, production build,
and mutation tests while preserving all CLI and API behavior from MVPs 1–3.

## Red

The acceptance contract covered disconnected and loading states, new-job form
validation, authenticated proxy headers, complete paginated history, active-job
polling, authoritative cohort totals, semantic exit-code and timeout states,
safe CSV export, and chronological audit rendering.

The first end-to-end hardening pass exposed missing cross-layer contracts:
dashboard field aliases, bounded API pagination, stable result statistics,
complete multi-page fetching, explicit test execution metadata, proxy
verification, and production browser scenarios. Focused tests captured those
gaps before the compatibility layer and hardened UI behavior were added.

## Green

The smallest complete dashboard slice added:

- a responsive Next.js application shell with local connection settings;
- a typed, authenticated client and restricted same-origin API proxy;
- job creation, full-history listing, status metrics, and active-job polling;
- completed and failed job detail views;
- cohort summaries, student result cards, test output, and JSON/CSV export; and
- an authenticated audit timeline linked back to grading jobs.

Backend compatibility additions supplied the aliases, pagination, cohort
statistics, and execution metadata needed by the UI without moving grading
logic into the frontend.

## Refactor

Common badges, buttons, cards, fields, dialogs, skeletons, empty states, and
query errors were extracted into reusable components. Result calculations,
duration formatting, and spreadsheet-safe CSV encoding moved into pure client
utilities. `mvp4_contract.py` isolated backend normalization, pagination, and
cohort aggregation for direct mutation testing.

The API client was refactored to fetch all job pages deterministically, surface
typed backend failures, and keep bearer/proxy mechanics outside page
components. The proxy was narrowed with protocol and host checks, no-store
responses, redirect rejection, and an upstream timeout.

## Validate

The completed MVP 4 snapshot (`7b36698`) was revalidated on 2026-08-18:

- Python regression suite: `79 passed`, including 53 unit, 11 integration, and
  4 executable API Gherkin tests.
- React unit and proxy integration suite: `21 passed` across 8 Vitest files.
- Production Playwright Gherkin suite: `3 passed`, covering complete paginated
  history, gradebook inspection and exports, and the audit trail.
- Backend mutation suite: `155/157` killed (`98.73%`). The two survivors are
  equivalent binary floating-point rounding mutations in `cohort_totals`.
- Frontend mutation suite: `65/65` killed (`100%`) across pagination,
  authenticated transport, result metrics, duration rules, and safe CSV export.
- ESLint, TypeScript checking, and the optimized Next.js production build
  passed. The generated application included `/jobs`, `/jobs/{id}`, `/audit`,
  `/settings`, and the restricted API proxy.
