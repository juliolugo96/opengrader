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
| `OPENGRADER_PDF_STORAGE_ROOT` | `.opengrader/pdfs` | Generated-ID PDF storage root |
| `OPENGRADER_PDF_MAX_UPLOAD_BYTES` | `10485760` | Maximum uploaded PDF bytes |
| `OPENGRADER_PDF_MAX_PAGES` | `200` | Maximum parsed PDF pages |
| `OPENGRADER_BILLING_ENABLED` | `false` | Enforce hosted subscription access and meter usage |
| `STRIPE_SECRET_KEY` | none | Server-only Stripe API key; required in hosted mode |
| `STRIPE_WEBHOOK_SECRET` | none | Stripe endpoint signing secret; required in hosted mode |
| `OPENGRADER_STRIPE_PRICE_ID` | none | Recurring metered Stripe Price used by Checkout |
| `OPENGRADER_STRIPE_METER_EVENT_NAME` | `opengrader_grading_units` | Event name of the configured Stripe meter |
| `OPENGRADER_PUBLIC_URL` | `http://localhost:3000` | Dashboard origin used for Stripe return URLs |
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
| `GET` | `/v1/jobs?status=&limit=&offset=` | `200` | Newest first; limit 1–100 |
| `GET` | `/v1/jobs/{id}` | `200` | State, request, reports, and error |
| `GET` | `/v1/jobs/{id}/result` | `200` | Available only after success |
| `GET` | `/v1/audit-events?limit=` | `200` | Chronological events; limit 1–500 |
| `POST` | `/v1/pdf-submissions` | `201` | Multipart `file`, `student_id`, and `title` |
| `GET` | `/v1/pdf-submissions?limit=&offset=` | `200` | Newest validated documents first |
| `GET` | `/v1/pdf-submissions/{id}` | `200` | Rubric, grade, annotations, and totals |
| `GET` | `/v1/pdf-submissions/{id}/document` | `200` | Original PDF, inline disposition |
| `PUT` | `/v1/pdf-submissions/{id}/grade` | `200` | Save draft or immutable final grade |
| `GET` | `/v1/pdf-submissions/{id}/feedback.pdf` | `200` | Finalized annotated feedback PDF |
| `GET` | `/v1/billing/overview` | `200` | Edition, entitlement, period, and usage delivery totals |
| `POST` | `/v1/billing/checkout` | `200` | Create Stripe Checkout from a validated billing email |
| `POST` | `/v1/billing/portal` | `200` | Create a Customer Portal session for the tenant |
| `POST` | `/v1/billing/webhook` | `200` | Verify and project a Stripe lifecycle event |

All `/v1` endpoints except the Stripe webhook return `401` for a missing or
invalid bearer key and `503` when the service has no configured keys. The
webhook requires a valid `Stripe-Signature` header over the unmodified request
body. The service supports one process only; multiple workers or hosts require
a future leased/distributed queue design.

## Grade a PDF

```sh
curl -X POST http://127.0.0.1:8000/v1/pdf-submissions \
  -H 'Authorization: Bearer development-only-key' \
  -F 'student_id=alice' \
  -F 'title=Final essay' \
  -F 'file=@essay.pdf;type=application/pdf'
```

Save a complete rubric using `PUT /v1/pdf-submissions/{id}/grade`. Criterion
IDs must be unique, every criterion needs exactly one score, scores cannot
exceed their criterion maximum, and annotation pages and normalized `x`/`y`
coordinates must be inside the document. Set `finalized` to `true` only when
editing is complete. The feedback export contains printable PDF text comments
and an `opengrader-feedback.json` attachment with the complete grading record.

## Enable hosted billing

Billing is off by default, and local grading remains unrestricted. For a hosted
deployment, create a Stripe meter whose event name matches
`OPENGRADER_STRIPE_METER_EVENT_NAME`, attach it to a recurring metered Price,
and configure that Price for Checkout:

```sh
export OPENGRADER_BILLING_ENABLED=true
export STRIPE_SECRET_KEY='sk_live_...'
export STRIPE_WEBHOOK_SECRET='whsec_...'
export OPENGRADER_STRIPE_PRICE_ID='price_...'
export OPENGRADER_STRIPE_METER_EVENT_NAME='opengrader_grading_units'
export OPENGRADER_PUBLIC_URL='https://grader.example.edu'
```

Register `POST /v1/billing/webhook` for these events:

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`

For local webhook testing, use Stripe CLI forwarding and copy the generated
`whsec_...` secret into `STRIPE_WEBHOOK_SECRET`:

```sh
stripe listen \
  --events checkout.session.completed,customer.subscription.created,customer.subscription.updated,customer.subscription.deleted \
  --forward-to http://127.0.0.1:8000/v1/billing/webhook
```

Hosted mode returns `402 Payment Required` for new jobs and PDF uploads until a
signed webhook projects an `active` or `trialing` subscription for that API-key
fingerprint. Each accepted job or PDF is one unit. Usage first enters the local
outbox, then the background worker submits a Stripe meter event using the outbox
UUID as its idempotency identifier. Stripe outages therefore do not roll back
accepted grading records.
