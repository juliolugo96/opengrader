# Roadmap

## MVP 1 — CLI autograding (complete)

- Validated YAML assignments
- Folder discovery
- Local and Docker runners
- Pass/fail scoring
- JSON and Markdown reports

## MVP 2 — Batch grading (current)

- Exit-code-based partial-credit rubrics
- Deterministic parallel workers
- Submission-level glob filters and bounded retries
- JSON, Markdown, and aggregate CSV export

Deferred from MVP 2: progress callbacks, resumable jobs, and plagiarism-export
hooks. These fit the persistent job model planned for MVP 3.

## MVP 3 — API

- FastAPI service around the grading engine
- Persistent jobs and result storage
- Authentication and audit events

## MVP 4 — UI

- React dashboard for assignments, runs, and feedback
- Instructor and student views

## MVP 5 — PDF grading

- PDF ingestion, rubrics, and annotations

## MVP 6 — Billing

- Stripe subscriptions and usage metering for hosted deployments

## MVP 7 — LMS integrations

- Canvas assignment and grade synchronization
- Additional LMS adapters behind a common interface
