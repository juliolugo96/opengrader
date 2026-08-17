# Architecture

OpenGrader is a batch pipeline with deliberately small interfaces:

```text
assignment YAML ──> validation ─┐
                               ├─> grading engine ─> result models ─> JSON + Markdown
submission folders ─> discovery ─> selection┘       │
                                                     ├─> retry/scoring policy
                                                     └─> Docker runner (default)
                                                          or local runner (opt-in)
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

Each test starts from a fresh copy of the submission. In Docker mode the source
is mounted read-only, copied into an in-memory workspace, and run without network
access. This makes tests independent and avoids changing submitted files.

Tests within a submission remain sequential; submissions may execute in
parallel. Ordered executor mapping ensures reports are deterministic regardless
of completion order. The runner protocol remains the main extension seam, so
future execution backends can be added without changing scoring or reports.
