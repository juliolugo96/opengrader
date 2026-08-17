# Architecture

OpenGrader is a synchronous pipeline with deliberately small interfaces:

```text
assignment YAML ──> validation ─┐
                               ├─> grading engine ─> result models ─> JSON + Markdown
submission folders ─> discovery┘         │
                                         └─> Docker runner (default)
                                              or local runner (opt-in)
```

## Components

- `config.py` defines the strict Pydantic assignment schema and translates YAML
  or validation failures into user-facing errors.
- `submissions.py` discovers visible direct child directories and sorts them for
  reproducible output.
- `runners.py` implements a small execution boundary. `DockerRunner` uses the
  Docker CLI; `LocalRunner` is a development fallback for trusted code.
- `grader.py` applies each pass/fail test to each submission and awards all or no
  points.
- `results.py` owns the serializable result schema and report rendering.
- `cli.py` coordinates the pipeline and presents a Rich terminal summary.

Each test starts from a fresh copy of the submission. In Docker mode the source
is mounted read-only, copied into an in-memory workspace, and run without network
access. This makes tests independent and avoids changing submitted files.

The runner protocol is the main extension seam. Future execution backends can be
added without changing configuration, grading, or report code.

