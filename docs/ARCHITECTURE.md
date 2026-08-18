# Architecture

OpenGrader is a batch pipeline with CLI and API entry points around deliberately
small interfaces:

```text
assignment YAML ──> validation ─┐
                               ├─> grading engine ─> result models ─> JSON + Markdown
submission folders ─> discovery ─> selection┘       │
                                                     ├─> retry/scoring policy
                                                     └─> Docker runner (default)
                                                          or local runner (opt-in)
```

```text
authenticated HTTP request ─> SQLite job + audit event ─> background worker
                                      │                         │
                                      └─ status/result API <────┘
```

```text
authenticated PDF upload ─> bounded server storage ─> strict PDF validation
                                      │                         │
                                      └─ SQLite draft <─────────┘
                                             │
                           rubric + page annotations + feedback
                                             │
                                      immutable finalization
                                             │
                            annotated PDF + embedded feedback JSON
```

## Components

- `config.py` defines the strict Pydantic assignment schema and translates YAML
  or validation failures into user-facing errors.
- `submissions.py` discovers visible direct child directories, sorts them for
  reproducible output, and selects a stable union of shell-style ID patterns.
- `runners.py` implements a small execution boundary. `DockerRunner` uses the
  Docker CLI; `LocalRunner` is a development fallback for trusted code.
- `grader.py` schedules submissions on a bounded thread pool, applies retries,
  and maps configured exit codes to full, partial, or zero credit.
- `results.py` owns the serializable result schema and JSON, Markdown, and CSV
  report rendering.
- `cli.py` coordinates the pipeline and presents a Rich terminal summary.
- `api.py` defines authenticated FastAPI routes and owns the worker lifespan.
- `api_models.py` defines the strict HTTP contract, state, and environment
  settings.
- `repository.py` owns durable SQLite transitions and append-only audit events.
- `worker.py` claims queued jobs and invokes the same grading pipeline used by
  the CLI, outside request handlers.
- `pdf_contract.py` contains pure rubric, score, annotation-page, and coordinate
  invariants.
- `pdf_grading.py` defines the PDF grading contract, strictly validates parsed
  documents, and renders feedback-preserving PDF exports.
- `pdf_repository.py` persists PDF metadata, draft/finalized grades, and audit
  events without handling uploaded bytes.
- `pdf_service.py` streams untrusted uploads into generated storage paths,
  enforces byte/page boundaries, and coordinates final export.

Each test starts from a fresh copy of the submission. In Docker mode the source
is mounted read-only, copied into an in-memory workspace, and run without network
access. This makes tests independent and avoids changing submitted files.

Tests within a submission remain sequential; submissions may execute in
parallel. Ordered executor mapping ensures reports are deterministic regardless
of completion order. The runner protocol remains the main extension seam, so
future execution backends can be added without changing scoring or reports.

The API's SQLite database is the source of truth. Its state machine is
`queued -> running -> succeeded|failed`, with interrupted running jobs returned
to `queued` on startup. MVP 3 deliberately runs one in-process worker in one API
process; distributed leases and cancellation are future concerns.

PDF submissions are separate from automated jobs. Their state machine is
`draft -> finalized`; finalization is intentionally immutable. PDF bytes live
under `OPENGRADER_PDF_STORAGE_ROOT/{generated-id}/`, while SQLite stores only
validated metadata and grading state. Annotation coordinates are normalized
from the page's top-left and translated into PDF points during export.
