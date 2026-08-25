# LMS Integrations Design

## Outcome

The LMS integration lets an authenticated instructor browse Canvas courses and assignments,
import an assignment into OpenGrader's local academic catalog, link existing
assignments, and synchronize completed automated or finalized PDF grades back to
Canvas. OpenGrader remains the source of its open assignment and result formats.

## Architecture

- `LmsAdapter` is the provider-neutral boundary for courses, assignments, and
  grade delivery. `LmsAdapterRegistry` makes later LMS adapters additive.
- `CanvasAdapter` owns Canvas REST shapes, bearer authentication, pagination,
  URL encoding, and grade submission. Tokens never enter browser responses,
  SQLite, logs, or audit details.
- `LmsRepository` stores local-to-external assignment links and idempotent grade
  delivery keys in SQLite alongside the existing audit stream.
- `LmsService` imports remote metadata into the academic assignment service and
  obtains grades only from successful jobs or finalized PDF submissions.
- Authenticated `/v1/lms/*` routes expose connection status, discovery, linking,
  importing, dry runs, and synchronization.

## Security and failure behavior

Canvas configuration is server-owned through environment variables. The base
URL must be an HTTPS origin without embedded credentials. Every path identifier
is percent encoded. Remote JSON is parsed into strict bounded models. An absent
or partial configuration fails closed, and sync never sends draft PDF grades or
results from incomplete jobs.

Each student/grade/source combination receives a stable delivery key. A
successful retry is skipped, while an upstream error is returned per student
without marking the grade delivered. Dry runs perform all local validation but
make no Canvas request or durable delivery record.

## Product surfaces

The Integrations workspace presents connection state, Canvas course and
assignment discovery, import/link actions, and grade-sync reports. The Plans
workspace describes Community, Hosted early access, and Institution/design
partner scope. Explicitly planned features remain labeled as planned.
