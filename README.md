# OpenGrader

OpenGrader is an open-source, local-first autograding CLI. It discovers one
submission per folder, runs an assignment's tests in isolated Docker containers,
and writes both JSON results and a Markdown summary.

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

Reports are written to `opengrader-results/results.json` and
`opengrader-results/summary.md`. Choose another location with
`--output-dir PATH`.

> [!WARNING]
> `--no-docker` executes submission commands on the host. A temporary copy keeps
> source folders clean, but it is not a security boundary. Only use it with code
> you trust.

## Assignment format

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
```

A test passes when its shell command exits with status `0`. It receives all its
configured points; any other exit status or a timeout receives zero. Test names
must be unique. Unknown YAML keys are rejected to catch mistakes early.

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
```

See [Architecture](docs/ARCHITECTURE.md), [security](docs/SECURITY.md), and the
[roadmap](docs/ROADMAP.md) for scope and design details.

