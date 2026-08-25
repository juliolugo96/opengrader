# API Architecture and Design

## Goal

The service exposes the local grading engine through an authenticated HTTP API with
durable jobs, result retrieval, and auditability. The API remains local-first:
requests refer to assignment and submission paths already available to the
server, while execution uses the existing Docker sandbox by default.

## API contract

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Unauthenticated liveness and readiness |
| `POST` | `/v1/jobs` | Validate and enqueue a grading job |
| `GET` | `/v1/jobs` | List recent jobs, optionally by status |
| `GET` | `/v1/jobs/{id}` | Inspect job state and metadata |
| `GET` | `/v1/jobs/{id}/result` | Retrieve a successful grading result |
| `GET` | `/v1/audit-events` | Inspect the append-only audit trail |

All `/v1` routes require `Authorization: Bearer <api-key>`. Keys are supplied
through `OPENGRADER_API_KEYS` and compared in constant time. Stored audit actors
are short SHA-256 key fingerprints; raw keys are never persisted or returned.

## Durable job state

```text
queued ──claim──> running ──complete──> succeeded
                      └────fail───────> failed
                         restart
                            └─────────> queued
```

SQLite is the source of truth for requests, state transitions, result JSON,
report locations, errors, timestamps, and audit events. Claims use an immediate
transaction so the managed worker cannot execute the same queued row twice.
Startup requeues interrupted `running` jobs.

## Execution boundary

The request handler performs no grading. It persists a `queued` job, records the
actor, signals the worker, and returns `202`. A lifespan-managed daemon worker
claims jobs and invokes the existing discovery, selection, runner, grading, and
report pipeline. Each job writes reports beneath `<output-root>/<job-id>/`.

The worker is in-process and supports one API process. Running multiple API
processes against one database is not supported because startup recovery cannot
distinguish a live worker's job from an interrupted job. Production
orchestration, distributed queues, leases, cancellation, and retention policies
remain future work.

## Failure and security behavior

- Missing or invalid credentials return `401`; an unconfigured key set returns
  `503` instead of silently disabling authentication.
- Invalid request shapes return `422` and never create a job.
- Configuration, discovery, Docker, and unexpected worker failures transition the
  job to `failed` and record a terminal audit event.
- Result access before success returns `409`; unknown resources return `404`.
- The API never accepts a caller-selected output directory.
- `no_docker` is explicit and retains batch grading's trusted-code warning in docs.
