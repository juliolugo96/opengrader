# Product Capability Checklist

- [x] `opengrader run` CLI command
- [x] Strict Pydantic validation for YAML configuration
- [x] Folder-based submission discovery
- [x] Docker execution with CPU, memory, process, filesystem, and network limits
- [x] Explicit local runner for trusted development fixtures
- [x] Pass/fail scoring
- [x] JSON results
- [x] Markdown summary
- [x] Unit and CLI integration tests
- [x] Runnable example
- [x] Architecture, security, roadmap, and premium documentation

## Batch grading

- [x] Backward-compatible partial-credit configuration
- [x] Stable submission filtering
- [x] Bounded best-attempt retries
- [x] Deterministic submission-level parallelism
- [x] Aggregate CSV report
- [x] Unit test suite
- [x] Multi-component integration test
- [x] Executable Gherkin end-to-end scenarios
- [x] Mutation testing configuration and validation
- [x] TDAID Plan, Red, Green, Refactor, and Validate record

## Authenticated API

- [x] Strict FastAPI request and response contracts
- [x] Authenticated job, result, listing, and audit routes
- [x] Fail-closed API-key configuration with non-secret actor fingerprints
- [x] Durable SQLite job state and restart recovery
- [x] Background grading outside request handlers
- [x] Per-job JSON, Markdown, and CSV reports
- [x] Unit and multi-component integration tests
- [x] Executable authenticated Gherkin workflow
- [x] Mutation testing configuration and validation
- [x] Local deployment, architecture, security, and TDAID documentation

Capability completion means the example command succeeds and the test suite passes. It
does not imply that Docker alone is sufficient for adversarial multi-tenant use;
see [SECURITY.md](SECURITY.md).

## Operations dashboard

- [x] Responsive React operations dashboard
- [x] Complete paginated job history and result drill-down
- [x] Cohort statistics, captured output, and report downloads
- [x] Accessible loading, empty, success, and failure states
- [x] Unit, proxy integration, Gherkin browser, and mutation tests

## PDF grading

- [x] Authenticated multipart PDF upload
- [x] Streamed byte limits, strict parsing, encryption rejection, and page limits
- [x] Durable PDF metadata and append-only audit events
- [x] Structured rubrics with bounded manual scores and criterion feedback
- [x] Page-specific normalized annotations and immutable finalization
- [x] Annotated PDF export with embedded structured feedback
- [x] PDF queue, authenticated preview, and grading workspace
- [x] Unit, integration, API Gherkin, browser Gherkin, and mutation tests
- [x] Architecture, security, API, and TDAID documentation

## Hosted billing

- [x] Billing disabled by default with unlimited local grading
- [x] Hosted active/trialing entitlement enforcement
- [x] Server-owned Stripe Checkout and Customer Portal sessions
- [x] Raw-body webhook signature verification
- [x] Idempotent event ledger and timestamp-ordered subscription projection
- [x] Durable, retryable, idempotent usage-meter outbox
- [x] Billing and usage dashboard with accessible subscription states
- [x] Unit, integration, API Gherkin, browser Gherkin, and mutation tests
- [x] Architecture, operations, security, and TDAID documentation

## LMS integrations

- [x] Provider-neutral LMS adapter registry
- [x] Server-owned Canvas authentication and same-origin bounded pagination
- [x] Canvas course and assignment discovery
- [x] Assignment import and existing-assignment linking
- [x] Successful automated and finalized PDF grade synchronization
- [x] Canvas, SIS, and login identifier strategies
- [x] Dry-run previews and idempotent delivery records
- [x] Localized instructor workspace and transparent plan comparison
- [x] Unit, integration, API Gherkin, browser Gherkin, and mutation tests
- [x] Real browser-to-API-to-SQLite persistence scenario
- [x] Architecture, operations, security, plans, and TDAID documentation
