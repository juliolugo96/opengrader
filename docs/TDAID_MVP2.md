# MVP 2 TDAID Record

OpenGrader MVP 2 follows Test-Driven AI Development:
Plan → Red → Green → Refactor → Validate.

## Plan

- Scope and architectural decisions: [MVP2_DESIGN.md](MVP2_DESIGN.md)
- Acceptance language: `tests/features/batch_grading.feature`
- Compatibility gate: every MVP 1 test remains green without fixture changes.
- Completion gate: unit, integration, Gherkin end-to-end, and mutation suites all
  execute; package and example commands succeed.

## Red

Executable contracts are added before their production behavior:

- unit tests specify configuration validation, scoring, filtering, retry, order,
  and report semantics;
- integration tests compose discovery, local execution, grading, and reports;
- Gherkin specifies the public CLI batch workflow.

Observed Red gate: `pytest` exited `2` with three collection errors because
`credit_for` and `select_submissions` did not exist. This verified that the new
contracts could not pass against the MVP 1 implementation.

## Green

Production changes were implemented in three increments without weakening the
contracts: scoring/statuses; selection/retry/concurrency; CSV/CLI orchestration.
Focused Green reached 27 tests before the full Gherkin and integration gate
reached 31.

## Refactor

With the full suite green, retry selection was refactored from mutable sentinel
state to an explicit attempt list and deterministic `max` policy. Types, report
rounding, documentation, and the mutation harness were tightened while rerunning
the suite after every change.

## Validate

Validation results:

- `pytest -m unit`: 23 passed
- `pytest -m integration`: 1 passed
- `pytest -m e2e`: 2 passed
- `pytest`: 37 passed
- `mutmut run`: 140/140 batch/scoring mutants killed
- exploratory whole-package mutation run: Docker execution was identified as
  uncovered by unit mutation tests; surviving changes were dominated by CLI and
  report wording. Docker remains validated with a real-container smoke test.
- local batch example: JSON and CSV content cross-checked successfully

The mutation gate intentionally focuses on the MVP 2 batch/scoring engine. It
does not claim that cosmetic strings or Docker CLI assembly have a 100% mutation
score. This scope is explicit so the number remains meaningful and repeatable.
