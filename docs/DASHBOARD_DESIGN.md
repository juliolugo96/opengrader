# Operations Dashboard Design

## Outcome

The operations dashboard adds a responsive web console around the authenticated API. An
instructor can connect to an OpenGrader host, create and monitor grading jobs,
inspect cohort and student-level results, export result data, and trace the
durable audit history. The dashboard does not execute submissions or duplicate
grading state; the API and SQLite remain the source of truth.

## Contract

```text
browser-local API URL + bearer key
  -> same-origin Next.js proxy
  -> authenticated OpenGrader API
  -> durable jobs, results, and audit events
  -> responsive instructor and student-result views
```

- Connection settings and the light, dark, or system theme are stored in a
  versioned browser `localStorage` record.
- The jobs workspace loads every API page for accurate totals, creates strict
  grading requests, and polls only while jobs are queued or running.
- Job detail presents queued, running, failed, and succeeded states explicitly.
- Successful jobs show authoritative cohort totals, per-student scores,
  per-test outcomes, exit codes, timeouts, captured output, and JSON/CSV export.
- The audit workspace shows the chronological job lifecycle, opaque API-key
  fingerprint, and linked job reference.
- Loading, empty, error, and disconnected states remain visible and actionable.
- The layout supports desktop and mobile navigation, keyboard interaction,
  semantic status text, and accessible dialogs and controls.

## Routes

| Route | Purpose |
| --- | --- |
| `/jobs` | Complete job history, summary metrics, and new-job action |
| `/jobs/{id}` | Live job state, failure details, gradebook, and exports |
| `/audit` | Authenticated chronological audit history |
| `/settings` | API endpoint, bearer key, theme, and connection test |

The root route redirects to `/jobs`. React Query owns request state, caching,
active-job polling, and invalidation. A typed client translates UI inputs to the
API contract and normalizes transport errors into user-facing messages.

## API compatibility additions

The dashboard extends the backend without changing the grading pipeline:

- `assignment_path` and `submission_filter` are accepted as public dashboard
  aliases for the persisted authenticated API job-request fields.
- Job listing has bounded `limit` and non-negative `offset` pagination.
- Completed results include stable cohort total points, maximum points, and
  student count.
- Pure compatibility, pagination, and aggregation rules live in
  `dashboard_contract.py` so UI-facing behavior is independently testable.

## Proxy and credential boundary

The browser calls a same-origin catch-all Next.js route instead of requiring
permissive CORS on the Python service. The proxy:

- accepts only HTTP or HTTPS API URLs;
- rejects URLs containing embedded credentials;
- permits only explicitly configured hostnames;
- forwards the bearer authorization, content type, query, and request body;
- disables redirects and response caching; and
- applies a 30-second upstream timeout.

The bearer key remains available to JavaScript because the dashboard stores it in
`localStorage`. The console is therefore intended for a trusted device and
origin. It does not provide user accounts, role-based access, a separate
student login, or protection from malicious script executing on the dashboard
origin.

## Presentation boundary

Client-side CSV generation quotes fields and neutralizes spreadsheet-formula
prefixes in student identifiers. Terminal output is rendered as text, never as
HTML. Long paths, logs, and tables use bounded or horizontally scrollable
containers so they do not break the responsive application shell.
