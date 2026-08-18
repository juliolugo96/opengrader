# Premium Strategy

OpenGrader's local CLI and core grading engine remain free and open source. Paid
offerings fund the operational features that institutions otherwise need to
build and maintain themselves.

## Free

- Local CLI grading
- Assignment schema and report formats
- Docker runner
- Community extensions and documentation

## Paid hosted or self-hosted edition

- Managed autoscaling workers and queues
- Role-based access, SSO, and audit retention
- Hosted result storage and operational backups
- LMS and identity integrations
- Usage analytics, support, and service-level commitments
- Enterprise deployment tooling and policy controls

The open formats and engine prevent lock-in: institutions can export assignments,
submissions, and results and return to the local CLI. Premium code should integrate
through stable interfaces rather than weakening or duplicating the free core.

MVP 6 implements the first paid boundary as an opt-in hosted subscription. It
meters accepted grading operations through a separate durable outbox while the
local CLI, API, PDF workflow, and report formats remain unrestricted.
