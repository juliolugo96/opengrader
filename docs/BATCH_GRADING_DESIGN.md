# Batch Grading Architecture and Design

## Goal

Batch grading turns the synchronous pass/fail grader into a deterministic batch grader. It
adds partial credit, submission filtering, bounded retries, parallel workers,
and CSV export without invalidating initial CLI assignment files or JSON consumers.

## Behavioral contract

### Partial credit

Tests still receive full credit when their command exits with code `0`. An
optional `partial_credit` mapping assigns a fraction from `0` through `1` to a
nonzero exit code from `1` through `255`:

```yaml
tests:
  - name: Hidden rubric
    command: python grade.py
    points: 10
    partial_credit:
      2: 0.75
      3: 0.50
      4: 0.25
```

Timeouts always earn zero. Unmapped nonzero exit codes earn zero. Earned points
are rounded to six decimal places. Existing configurations need no changes.

### Batch controls

- `--workers/-j` grades submissions concurrently. Tests within one submission
  remain sequential.
- `--submission/-s PATTERN` may be repeated and selects student IDs with
  case-sensitive shell-style patterns. Results are deduplicated and retain
  discovery order. An unmatched pattern is an error instead of a silent no-op.
- `--retries N` reruns any test that has not earned full credit, using a fresh
  workspace each time. The best attempt determines the score; full credit ends
  retries early. Attempt count is retained in JSON.

### Reports

`results.json` and `summary.md` remain and gain status/attempt metadata. A new
`results.csv` contains one stable, spreadsheet-friendly row per submission.
Result order never depends on worker completion order.

## Component design

```text
discovery -> pattern selection -> batch engine -> report writers
                                  |     |
                                  |     +-> retry/scoring policy
                                  +-> bounded thread pool -> existing runner
```

The execution runners remain unaware of scoring and batching. The grading
engine owns retry policy and uses a `ThreadPoolExecutor` only at submission
boundaries. Pure scoring logic maps execution outcomes to credit fractions.

## Risks and controls

- Parallel runners can finish nondeterministically; ordered executor mapping and
  input-indexed assembly keep reports stable.
- Retries could inflate grades unexpectedly; the behavior is explicit, bounded,
  defaults to zero, and records attempts.
- Float multiplication can create report noise; public scores are rounded to six
  decimal places.
- Pattern typos can silently exclude work; every supplied pattern must match.
- Mutation testing can be slow and presentation mutations add little confidence;
  the repeatable gate targets the high-risk batch/scoring engine. Broader
  exploratory runs are recorded separately and survivors are reviewed.
