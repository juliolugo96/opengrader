# Assignment YAML Reference

An assignment file describes the execution environment, resource limits, test
commands, and scoring policy for one kind of submission. The same file works
with the CLI, authenticated API, and operations dashboard.

OpenGrader validates the complete document before discovering or running any
submission. Unknown fields are rejected, which catches spelling mistakes but
also means new options must be added to the schema deliberately.

## Minimal implementation

Only an assignment name and one test are required:

```yaml
name: Hello world
tests:
  - name: Program runs
    command: python solution.py
```

This expands to the following defaults:

- image: `python:3.12-slim`
- assignment timeout: 10 seconds
- memory: 256 MiB
- CPUs: 1
- process limit: 128
- test points: 1
- no setup command
- no partial-credit exit codes

Run it against a directory containing one visible folder per submission:

```sh
opengrader run assignment.yaml submissions/
```

## Full implementation (all fields)

This example uses every currently supported field:

```yaml
name: Data structures project
image: ghcr.io/example/cs-grader@sha256:replace-with-real-digest
setup: python -m compileall -q .
timeout_seconds: 20
memory_mb: 512
cpus: 2
pids_limit: 128
tests:
  - name: Module imports
    command: python -c "import solution"
    points: 1

  - name: Functional rubric
    command: grader evaluate --submission . --rubric correctness
    points: 7
    timeout_seconds: 10
    partial_credit:
      2: 0.75
      3: 0.5
      4: 0.25

  - name: Performance budget
    command: grader evaluate --submission . --rubric performance
    points: 2
    timeout_seconds: 5
    partial_credit:
      2: 0.5
```

Its maximum score is 10 points. Exit code `0` always earns full credit. For the
functional rubric, exit codes `2`, `3`, and `4` earn 75%, 50%, and 25% of seven
points respectively. Any other nonzero exit code earns zero.

## Top-level fields

| Field | Type | Required | Default | Validation and meaning |
| --- | --- | --- | --- | --- |
| `name` | string | yes | — | Non-blank display name used in reports |
| `image` | string | no | `python:3.12-slim` | Non-blank Docker image reference |
| `setup` | string or null | no | null | Non-blank shell command run before every test attempt |
| `timeout_seconds` | number | no | `10` | Greater than 0 and at most 3600; includes setup and test execution |
| `memory_mb` | integer | no | `256` | 32 through 32768; Docker memory and writable workspace limit |
| `cpus` | number | no | `1` | Greater than 0 and at most 32 |
| `pids_limit` | integer | no | `128` | 16 through 4096 processes |
| `tests` | list | yes | — | At least one test; names must be unique after trimming |

Resource fields are enforced by the Docker runner. Local mode still enforces
the command timeout, but it does not enforce the YAML memory, CPU, or process
limits.

## Test fields

| Field | Type | Required | Default | Validation and meaning |
| --- | --- | --- | --- | --- |
| `name` | string | yes | — | Non-blank name, unique within the assignment |
| `command` | string | yes | — | Non-blank shell command executed from the submission workspace |
| `points` | number | no | `1` | Must be greater than 0 |
| `timeout_seconds` | number or null | no | assignment timeout | Greater than 0 and at most 3600 |
| `partial_credit` | map of integer to number | no | `{}` | Exit codes 1–255 mapped to fractions from 0 through 1 |

The assignment maximum is the sum of all test points. Public earned scores are
rounded to six decimal places.

## Execution lifecycle

For every submission and every test attempt, OpenGrader creates a fresh
workspace:

```text
submission folder
  -> fresh local copy or fresh Docker container
  -> setup command, when configured
  -> test command, only when setup succeeds
  -> exit code, stdout, stderr, timeout, and duration
  -> full, partial, or zero credit
```

Important consequences:

- Tests for one submission run sequentially, but they do not share generated
  files because each test gets a fresh workspace.
- `setup` runs again before every test and every retry. Use it for compilation,
  validation, or preparation that the current test needs.
- A failing setup prevents that attempt's test command from running.
- The test timeout covers both setup and the test command.
- Retries also use fresh workspaces. OpenGrader keeps the highest-credit attempt
  and stops early after full credit.
- Test commands run through `/bin/sh`. Use POSIX shell syntax or explicitly
  invoke another shell that exists in the image.
- Standard output and error are captured in result JSON and the dashboard.

The Docker runner copies the read-only submission into writable `/workspace`,
sets `HOME=/tmp`, disables Python bytecode writes, and runs the command there.
The container root is read-only; `/workspace` and `/tmp` are writable temporary
filesystems.

## Scoring and partial credit

Scoring is exit-code based:

| Outcome | Credit |
| --- | --- |
| Exit code `0` | 100% |
| Mapped nonzero exit code | Configured fraction × test points |
| Unmapped nonzero exit code | 0% |
| Timeout | 0% |
| Process could not provide an exit code | 0% |

Example:

```yaml
- name: Hidden correctness rubric
  command: course-grader correctness .
  points: 8
  partial_credit:
    2: 0.75 # 6 points
    3: 0.5  # 4 points
    4: 0.25 # 2 points
```

The command decides which exit code represents a rubric tier. This makes the
format compatible with ordinary test tools, custom scripts, linters, and
grader binaries without embedding tool-specific result formats in OpenGrader.

Partial credit is configured per test. There are no category weights; express
weighting directly through each test's `points` value.

## Submission layout and selection

Every visible direct child directory is one submission, and its directory name
is the student or submission ID:

```text
submissions/
├── alice/
│   ├── solution.py
│   └── README.md
├── bob/
│   └── solution.py
└── .ignored-fixture/
```

Nested directories inside `alice` or `bob` are part of that submission. Hidden
direct child directories are ignored. Submissions are sorted case-insensitively
for deterministic reports.

Selection, concurrency, and retry count are run controls rather than assignment
policy, so they are CLI or API options instead of YAML fields:

```sh
opengrader run assignment.yaml submissions/ \
  --workers 8 \
  --retries 2 \
  --submission 'section-a-*' \
  --submission 'late-*'
```

- `--workers/-j`: 1–64 concurrent submissions.
- `--retries`: 0–10 extra attempts for any test that did not earn full credit.
- `--submission/-s`: repeatable, case-sensitive shell pattern. Every pattern
  must match at least one submission.

The authenticated API exposes equivalent `workers`, `retries`, and
`submission_patterns` request fields.

## How flexible is the format?

`command` can invoke anything present in the selected image, so assignments are
not restricted to Python or to a particular testing framework. Common patterns
include:

| Assignment | Image/toolchain | Command style |
| --- | --- | --- |
| Python function | Python image | `python -c` assertions or `unittest` |
| JavaScript module | Node image | `node -e` or a dependency-free test runner |
| C/C++ program | GCC/Clang image | Compile in `setup`, execute with piped input |
| Java program | JDK image | Compile in `setup`, execute the main class |
| Shell exercise | Alpine image | `sh -n`, pipelines, and file assertions |
| SQL query | Python/SQLite image | Build an ephemeral database and assert rows |
| Static website | Python/Node image | Parse markup, inspect accessibility, lint assets |
| Course-specific rubric | Custom pinned image | Call a grader binary and map rubric exit codes |

See the complete [assignment gallery](../examples/assignments/README.md) for
working definitions of each pattern.

### Using standard test frameworks

If dependencies are already available in the image or included with the
submission, a test can call the framework directly:

```yaml
tests:
  - name: Unit test suite
    command: python -m unittest discover -s tests -v
    points: 8
  - name: Static analysis
    command: ruff check .
    points: 2
```

Docker grading has no network access. Do not depend on `pip install`, `npm
install`, or remote services during a test. Build a pinned course image with
the required dependencies and grader-owned assets instead.

### Custom images

A custom image is the main extension mechanism for complex assignments. It can
contain compilers, libraries, test fixtures, linters, and a rubric executable.
The image must contain `/bin/sh` and `cp`, because the Docker runner uses both
to prepare the workspace. Pull or build the image before grading, and pin
production images by digest because mutable tags can change behavior.

Keep secrets out of images and YAML. A test command and its arguments are part
of the assignment definition and should not be treated as confidential.

## YAML and shell quoting

YAML and the shell both interpret punctuation. These patterns avoid most
surprises:

```yaml
# Quote commands containing YAML-sensitive characters.
command: 'test "$(cat answer.txt)" = "answer: 42"'

# Use a folded block for a readable multi-step shell command.
command: >-
  python cli.py divide 1 0 >stdout.txt 2>stderr.txt;
  code=$?;
  test "$code" -eq 2 && grep -qi "zero" stderr.txt
```

Use `>-` when several visual YAML lines should become one shell command. Use
`|` only when literal newlines are meaningful. Avoid Bash-only syntax unless
the command explicitly starts Bash and the selected image provides it.

`partial_credit` keys should be written as YAML integers:

```yaml
partial_credit:
  2: 0.5
```

## Validation and troubleshooting

Validate a file without running submissions:

```sh
python -c "from pathlib import Path; from opengrader.config import load_assignment; print(load_assignment(Path('assignment.yaml')))"
```

Common failures:

- `extra inputs are not permitted`: a field is misspelled or unsupported.
- `tests: List should have at least 1 item`: at least one test is required.
- `test names must be unique`: two trimmed test names are equal.
- immediate command failure: the image lacks the named executable or expected
  submission file.
- Docker-only success or local-only success: the two environments have
  different tools, shells, permissions, or dependencies.
- timeout during compilation: increase the assignment or per-test timeout; the
  limit includes setup.

For trusted fixtures, `--no-docker` is convenient for iteration. It runs as the
current host user and is not a security boundary. Use Docker for untrusted
submissions.

## Current boundaries

The YAML schema intentionally stays small. It does not currently have native
fields for:

- environment variables or secrets;
- service containers, databases, or network dependencies;
- per-test images, CPU, memory, or process limits;
- shared build artifacts between tests;
- dependency graphs or conditional test execution;
- input/output matcher objects or regular-expression assertions;
- category weights separate from test points;
- file artifact collection; or
- plagiarism detection hooks.

Shell commands and custom images can implement many of these testing patterns,
but they do not change OpenGrader's isolation or persistence model. Features
that require networked services, secrets, or multi-container orchestration need
an explicit future schema and runner design rather than ad hoc shell access.
