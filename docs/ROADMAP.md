# Roadmap

## MVP 1 — CLI autograding (complete)

- Validated YAML assignments
- Folder discovery
- Local and Docker runners
- Pass/fail scoring
- JSON and Markdown reports

## MVP 2 — Batch grading (complete)

- Exit-code-based partial-credit rubrics
- Deterministic parallel workers
- Submission-level glob filters and bounded retries
- JSON, Markdown, and aggregate CSV export

Deferred from MVP 2: progress callbacks and plagiarism-export hooks.

## MVP 3 — API (complete)

- FastAPI service around the grading engine (complete)
- Persistent SQLite jobs and result metadata (complete)
- API-key authentication and audit events (complete)
- In-process background grading and restart recovery (complete)
- Local deployment and API operations documentation (complete)

## MVP 4 — UI (complete)

- React dashboard for assignments, runs, and feedback
- Instructor and student views

## MVP 5 — PDF grading (complete)

- Bounded, strict PDF ingestion with durable metadata
- Rubric-based manual grading and immutable finalization
- Normalized page annotations and feedback-preserving PDF export
- Instructor dashboard and authenticated document preview

## MVP 6 — Billing

- Stripe subscriptions and usage metering for hosted deployments

## MVP 7 — LMS integrations

- Canvas assignment and grade synchronization
- Additional LMS adapters behind a common interface
