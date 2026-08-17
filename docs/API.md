# API Operations

MVP 3 provides a local, single-process FastAPI service. It accepts paths already
visible to the host; it does not upload assignment or submission archives.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENGRADER_API_KEYS` | none | Comma-separated bearer keys; at least one is required for `/v1` |
| `OPENGRADER_DATABASE` | `.opengrader/jobs.db` | SQLite job and audit database |
| `OPENGRADER_OUTPUT_ROOT` | `.opengrader/reports` | Per-job report root |
| `OPENGRADER_POLL_INTERVAL` | `0.25` | Idle worker poll interval in seconds |
| `OPENGRADER_HOST` | `127.0.0.1` | Uvicorn bind host |
| `OPENGRADER_PORT` | `8000` | Uvicorn bind port |

Use a long random key and keep it outside shell history and source control. Start
one service process with `opengrader-api`. Interactive OpenAPI documentation is
available at `/docs`; `/health` is public and reports whether authentication is
configured.

## Create and inspect a job

```sh
export OPENGRADER_API_KEYS='development-only-key'
opengrader-api
```

```sh
curl -sS -X POST http://127.0.0.1:8000/v1/jobs \
  -H 'Authorization: Bearer development-only-key' \
  -H 'Content-Type: application/json' \
  -d '{
    "assignment_file": "examples/assignment.yaml",
    "submissions_dir": "examples/submissions",
    "workers": 2,
    "retries": 1,
    "submission_patterns": ["*"]
  }'
```

The response is `202 Accepted` with a UUID and `queued` state. Use that UUID in:

```sh
curl -sS -H 'Authorization: Bearer development-only-key' \
  http://127.0.0.1:8000/v1/jobs/JOB_ID

curl -sS -H 'Authorization: Bearer development-only-key' \
  http://127.0.0.1:8000/v1/jobs/JOB_ID/result
```

Result access returns `409` until the job succeeds. A failed job exposes its
error in the job representation. Reports are stored under
`OPENGRADER_OUTPUT_ROOT/JOB_ID/`.

## Endpoints

| Method | Path | Success | Notes |
| --- | --- | --- | --- |
| `GET` | `/health` | `200` | Public liveness/configuration check |
| `POST` | `/v1/jobs` | `202` | Enqueue a strict job request |
| `GET` | `/v1/jobs?status=&limit=` | `200` | Newest first; limit 1–100 |
| `GET` | `/v1/jobs/{id}` | `200` | State, request, reports, and error |
| `GET` | `/v1/jobs/{id}/result` | `200` | Available only after success |
| `GET` | `/v1/audit-events?limit=` | `200` | Chronological events; limit 1–500 |

All `/v1` endpoints return `401` for a missing or invalid bearer key and `503`
when the service has no configured keys. The service supports one process only;
multiple workers or hosts require a future leased/distributed queue design.
