# Roadmap

## CLI autograding (complete)

- Validated YAML assignments
- Folder discovery
- Local and Docker runners
- Pass/fail scoring
- JSON and Markdown reports

## Batch grading (complete)

- Exit-code-based partial-credit rubrics
- Deterministic parallel workers
- Submission-level glob filters and bounded retries
- JSON, Markdown, and aggregate CSV export

Future enhancements include progress callbacks.

## Authenticated API (complete)

- FastAPI service around the grading engine (complete)
- Persistent SQLite jobs and result metadata (complete)
- API-key authentication and audit events (complete)
- In-process background grading and restart recovery (complete)
- Local deployment and API operations documentation (complete)

## Operations dashboard (complete)

- React dashboard for assignments, runs, and feedback
- Instructor and student views

## PDF grading (complete)

- Bounded, strict PDF ingestion with durable metadata
- Rubric-based manual grading and immutable finalization
- Normalized page annotations and feedback-preserving PDF export
- Instructor dashboard and authenticated document preview

## Hosted billing (complete)

- Optional hosted subscription enforcement with free local grading
- Stripe Checkout, Customer Portal, and signed lifecycle webhooks
- Idempotent, ordered subscription projections
- Durable grading-unit metering with retry-safe Stripe delivery

## Professor workspaces and localization (complete)

- Visual assignment authoring with no configuration-file knowledge required
- Institution, course, academic-period, and section organization
- Automated-check templates plus written/PDF assignment workflows
- Saved-assignment launch and PDF-submission association
- English, Spanish, and Simplified Chinese dashboard support

## LMS integrations (complete)

- Canvas course and assignment discovery
- Canvas assignment import and existing-assignment linking
- Finalized PDF and successful automated grade synchronization
- SIS, Canvas-user, and login identifier strategies
- Dry-run previews and idempotent grade delivery records
- Additional LMS adapters behind a common interface
- Localized instructor integration workspace
- Transparent Community, Hosted, and Institution plans experience

## Similarity review (complete)

- Assignment-scoped PDF corpus snapshots
- Versioned Unicode normalization and structural winnowing
- Bounded inverted-index candidate retrieval
- Containment, Jaccard, coverage, and short evidence excerpts
- Durable jobs, immutable reports, restart recovery, and audit events
- Human-review language with no misconduct verdict
- Localized professor workspace and Gherkin browser/API journeys

Future enhancements can add source-code tokenizers, configurable boilerplate
suppression, and evaluated semantic candidate retrieval behind the existing
service and report contracts.
