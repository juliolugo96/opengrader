# OpenGrader

OpenGrader is an open-source, local-first autograder with CLI and authenticated
HTTP interfaces. It discovers one submission per folder, runs assignment tests
in isolated Docker containers, and writes JSON, Markdown, and CSV reports. The
authenticated service and dashboard add durable asynchronous jobs, an audit
trail, and manual PDF grading with rubrics, page annotations, and
feedback-preserving exports. Assignment-scoped similarity review adds versioned
structural signals and explainable excerpts for instructor review without
issuing academic-misconduct verdicts. Hosted deployments can optionally enforce Stripe
subscriptions and meter accepted grading operations while local grading stays
free.

The professor-facing dashboard organizes work by institution, course, academic
period, and section. Its guided builder supports automated checks and written or
PDF work without exposing engine configuration files. The interface supports
English, Spanish, and Simplified Chinese. See [Professor Workspaces](docs/PROFESSOR_WORKSPACES.md).

## Requirements

- Python 3.12 or newer
- Docker (recommended for untrusted submissions)

## Install

Create a virtual environment, then install the package:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Quick start

Run the included example without Docker:

```sh
opengrader run examples/assignment.yaml examples/submissions --no-docker
```

Or use the default Docker sandbox:

```sh
opengrader run examples/assignment.yaml examples/submissions
```

Reports are written to `opengrader-results/results.json`,
`opengrader-results/summary.md`, and `opengrader-results/results.csv`. Choose
another location with `--output-dir PATH`.

Batch options can be combined:

```sh
opengrader run assignment.yaml submissions/ \
  --workers 4 \
  --submission 'section-a-*' \
  --submission 'late-*' \
  --retries 1
```

`--submission/-s` accepts case-sensitive shell patterns and may be repeated.
Every pattern must match at least one folder. `--workers/-j` runs submissions in
parallel while keeping report order stable. `--retries` grants additional fresh
attempts and retains the highest-scoring attempt.

> [!WARNING]
> `--no-docker` executes submission commands on the host. A temporary copy keeps
> source folders clean, but it is not a security boundary. Only use it with code
> you trust.

## HTTP API

Configure at least one API key and start the single-process local service:

```sh
export OPENGRADER_API_KEYS='replace-with-a-long-random-key'
opengrader-api
```

Submit a job that uses paths visible to the API host:

```sh
curl -X POST http://127.0.0.1:8000/v1/jobs \
  -H 'Authorization: Bearer replace-with-a-long-random-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "assignment_file": "examples/assignment.yaml",
    "submissions_dir": "examples/submissions"
  }'
```

The request returns `202` immediately. Poll `/v1/jobs/{id}` and retrieve the
completed result from `/v1/jobs/{id}/result`. See the [API operations guide](docs/API.md)
for every endpoint and environment setting. API-side `no_docker: true` has the
same trusted-code warning as `--no-docker`.

## PDF grading

Open the dashboard's **PDF grading** section to upload a document, define a
rubric, record criterion feedback, place normalized page comments, and finalize
the grade. Finalized grades are immutable and can be downloaded as annotated
PDFs containing an embedded structured feedback record. The default upload
limits are 10 MiB and 200 pages; see the [API operations guide](docs/API.md) and
[PDF grading design](docs/PDF_GRADING_DESIGN.md).

## Professor assignment workspace

Open **Assignments** to create, edit, filter, and launch course work. Choose
automated evaluation or written/PDF grading, enter the institution, course,
period, and section, then use the guided fields. Programming templates cover
Python, JavaScript, and C; advanced resource controls remain available when
needed. Written assignments appear in the PDF upload selector so submissions
stay attached to the correct course context.

Choose English, Español, or 简体中文 in **Settings**. The preference stays in the
current browser and updates the document language for assistive technology.

## Similarity review

Open **Similarity review**, choose a written/PDF assignment with at least two
submissions, and start a durable structural analysis. The report shows bounded
candidate pairs, scores, and evidence excerpts. It is evidence for human review,
not a plagiarism verdict. See the [similarity review design](docs/SIMILARITY_REVIEW_DESIGN.md).

## Hosted billing

Billing is disabled by default. In hosted mode, the **Billing & usage** dashboard
starts Stripe Checkout, opens the Customer Portal, displays webhook-derived
subscription state, and tracks durable usage delivery. Access is granted only
from signed Stripe lifecycle webhooks; Checkout redirects are never trusted as
proof of payment. See the [hosted billing design](docs/HOSTED_BILLING_DESIGN.md) and
[API operations guide](docs/API.md) for Stripe meter, Price, webhook, and
environment configuration.

## Canvas LMS integration

The localized **LMS integrations** workspace lets instructors browse
Canvas courses, import an assignment into the open local catalog, link existing
work, preview synchronization, and return finalized PDF or successful automated
grades using Canvas, SIS, or login identifiers. Successful delivery is
idempotent, and Canvas credentials remain in the server environment.

See the [LMS integration design](docs/LMS_INTEGRATIONS_DESIGN.md), [Canvas API operations](docs/API.md#connect-canvas),
and [edition comparison](docs/PLANS.md).

## Assignment format

The format ranges from a two-field minimal definition to pinned custom images,
resource limits, setup commands, per-test timeouts, weighted points, and
exit-code partial credit. See the complete [assignment YAML reference](docs/ASSIGNMENT_FORMAT.md)
and the [multi-language assignment gallery](examples/assignments/README.md).

```yaml
name: Intro to Python
image: python:3.12-slim
timeout_seconds: 10
memory_mb: 256
cpus: 1
pids_limit: 128
setup: python -m compileall -q . # optional; runs before every test
tests:
  - name: Program exits successfully
    command: python solution.py
    points: 2
  - name: Unit tests pass
    command: python -m unittest -q
    points: 3
    timeout_seconds: 20 # optional per-test override
    partial_credit:      # optional exit-code-to-credit-fraction mapping
      2: 0.75
      3: 0.50
```

A test receives full credit when its shell command exits with status `0`.
Configured nonzero exit codes can receive a fractional score; unmapped failures
and timeouts receive zero. Test names must be unique. Unknown YAML keys are
rejected to catch mistakes early.

Every visible direct child directory of the submissions path is treated as one
submission, and its folder name becomes its student ID:

```text
submissions/
├── alice/
│   └── solution.py
└── bob/
    └── solution.py
```

## Development

```sh
pytest
pytest -m unit
pytest -m integration
pytest -m e2e
mutmut run
```

The client also includes Playwright Gherkin coverage plus a real browser →
Next.js proxy → FastAPI → temporary SQLite → browser persistence journey:

```sh
cd client
npm run test:e2e
```

See the [LMS integration design](docs/LMS_INTEGRATIONS_DESIGN.md), [TDAID record](docs/TDAID_LMS_INTEGRATIONS.md),
[end-to-end testing guide](docs/E2E_TESTING.md),
[professor workspace guide](docs/PROFESSOR_WORKSPACES.md),
[plans](docs/PLANS.md),
[architecture](docs/ARCHITECTURE.md), [security](docs/SECURITY.md), and
[roadmap](docs/ROADMAP.md) for scope and design details.
