# Future MVP Prompts

These prompts are deliberately scoped so each phase can be implemented and
reviewed independently.

## MVP 3 — API

Add a FastAPI service that creates grading jobs, exposes job status, and returns
existing result models. Run grading outside request handlers, persist state, add
authentication and audit events, and document local deployment.

## MVP 4 — UI

Build a React dashboard on the API for uploading assignments and submissions,
following run progress, inspecting captured output, and downloading reports.
Include accessible loading, empty, success, and failure states.

## MVP 5 — PDF grading

Add PDF submissions, rubric-based manual grading, page annotations, and an export
that preserves feedback. Treat uploaded documents as untrusted input and test
malformed and oversized files.

## MVP 6 — Billing

Add Stripe subscriptions and usage metering to the hosted edition. Keep all
local grading features free. Make webhook processing idempotent and retain a
clear separation between billing state and grading records.

## MVP 7 — LMS integrations

Add a Canvas adapter for importing rosters and assignments and exporting grades.
Use least-privilege credentials, dry-run grade writes, idempotency keys, and a
generic adapter interface for future LMS providers.
