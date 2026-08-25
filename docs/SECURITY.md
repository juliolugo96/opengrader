# Security

Student submissions are untrusted code. OpenGrader uses Docker as a practical isolation
boundary, but Docker containers are not equivalent to dedicated virtual machines.

## Similarity evidence

Similarity review is restricted to the selected assignment and snapshots only
submission identifiers and policy in its job request. Extracted document text
is processed in memory and is never included in logs or audit details. Reports
store only bounded evidence excerpts. Same-student resubmissions are excluded,
short or unextractable documents are explicitly indeterminate, and every durable
state transition is audited. Similarity bands are not misconduct verdicts.

## Default controls

For every test, OpenGrader:

- starts a new container and removes it afterward;
- disables networking;
- applies memory, CPU, and process-count limits;
- makes the container root filesystem read-only;
- mounts the submitted folder read-only;
- copies the submission into a fresh temporary in-container workspace; and
- enforces a host-side timeout, force-removing timed-out containers.

Do not mount the Docker socket, credentials, SSH agents, or sensitive host paths
into grading containers. Use narrowly built, pinned images; keep the host kernel
and Docker current; and run production grading on disposable, dedicated workers.
Image tags in assignment files are mutable, so production systems should pin
images by digest.

## Local mode

`--no-docker` runs shell commands directly as the current OS user. A disposable
copy protects the original submission folder from ordinary writes, but the code
can still read, modify, or delete anything that user can access and can use the
network. Only use local mode for trusted fixtures.

## HTTP API

All `/v1` routes require a bearer key from `OPENGRADER_API_KEYS`. OpenGrader
fails closed with `503` when no keys are configured, compares supplied keys in
constant time, and writes only a short SHA-256 fingerprint to audit records.
Raw keys are neither persisted nor returned.

## Hosted billing

Billing is disabled by default. When enabled, Stripe secret and webhook keys
remain server-only and are excluded from the `ApiSettings` representation. The
webhook endpoint is the only unauthenticated `/v1` route; it reads the exact raw
request body and verifies the `Stripe-Signature` header before processing.
Browser redirects and Checkout success query parameters never grant access.

Subscription events must carry OpenGrader's opaque key fingerprint metadata and
the configured metered Price. Event IDs are stored before applying changes, and
older event timestamps cannot overwrite a newer subscription projection. Only
`active` and `trialing` states authorize new hosted work. Stripe-hosted URLs are
created from server configuration rather than accepting arbitrary prices or
return URLs from clients.

Use restricted Stripe keys where available, rotate secrets through the hosting
platform, register only the documented webhook event types, and terminate TLS
before the API. Do not log webhook bodies or Stripe objects: they can contain
customer billing data. Limit request size for the webhook route and monitor
repeated signature failures.

## PDF uploads

Uploaded PDFs are untrusted complex documents. OpenGrader stores them under a
generated UUID rather than a client-controlled path, streams them in bounded
chunks, rejects them above the configured byte limit, parses them in strict
mode, and rejects encrypted, empty, malformed, or excessive-page documents.
Original files and generated feedback are outside the dashboard's static root.

These controls reduce exposure but do not make PDF parsing risk-free. Keep
`pypdf` current, run the API as a least-privilege user, keep the PDF storage root
free of secrets, and configure an equal or lower request-body limit at the
reverse proxy so oversized requests are rejected before application parsing.
Returned PDFs may still contain active features already present in the original;
instructors should use a patched viewer and avoid trusting embedded links or
attachments. OpenGrader adds only printable text annotations and its own JSON
feedback attachment.

## Canvas LMS integration

The Canvas access token is a privileged server credential. It is loaded only
from the process environment, excluded from settings representations, and never
stored in SQLite, browser storage, API responses, or audit details. Use a
dedicated least-privilege Canvas token, rotate it outside OpenGrader, and do not
place it in assignment configuration or logs.

The configured Canvas address must be a credential-free HTTPS origin. Course,
assignment, and student identifiers are percent encoded. Pagination is limited
to 50 pages and every next link must retain the exact configured origin so a
malicious or compromised response cannot forward the bearer token elsewhere.
Deployments should still enforce outbound network policy so the API can reach
only the intended Canvas host.

Only finalized PDF grades and successful automated-job results can be sent.
Dry runs contact no grade endpoint and write no delivery state. A successful
delivery is recorded under a deterministic key, making normal replay safe.
Remote partial failure remains visible in the response and is not marked
delivered, so an instructor can retry it. Review student-ID strategy before the
first live sync; choosing the wrong Canvas, SIS, or login namespace can update
the wrong enrollment if institutional identifiers are inconsistent.

API requests contain server-local paths, so authenticated callers can ask the
service to read assignment and submission directories accessible to its OS
account. Treat keys as privileged credentials, run OpenGrader under a dedicated
least-privilege account, and keep its readable filesystem narrow. Bind to
loopback by default. Any network deployment needs TLS and authentication at a
trusted reverse proxy in addition to the application key.

authenticated API supports a single API process with one managed worker. Do not run multiple
processes against the same database. As with the CLI, setting `no_docker: true`
executes trusted submission code with the API process user's host permissions.

## Known deployment limitations

- Assignment authors are trusted; their image and commands are executed as
  configured.
- Output size is not capped, and very large output may consume host memory.
- Docker daemon authorization is outside OpenGrader.
- Strong multi-tenant deployments need worker isolation, image policy, quotas,
  centralized audit logs, and additional sandboxing such as microVMs.
- API keys have no built-in rotation, scope, expiration, or rate limiting.
- A hosted subscription is keyed to its API-key fingerprint. Rotating that key
  requires an operator migration of the billing account in this release.
- PDF validation is in-process rather than isolated in a parser sandbox.
- Hosted billing uses a single-process usage worker; horizontally scaled
  deployments need leased outbox claims or a distributed queue.
- Stripe event timestamps have one-second resolution. Equal-timestamp lifecycle
  events rely on delivery order; operators should reconcile anomalous accounts
  against Stripe before granting manual overrides.
- Canvas grade delivery is synchronous; large cohorts or upstream rate limits
  need a future leased outbox worker with provider-aware backoff.

Report vulnerabilities privately to the project maintainers rather than opening
a public issue containing exploit details.
