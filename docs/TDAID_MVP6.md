# TDAID Record — MVP 6 Hosted Billing

## Plan

The increment is split into pure entitlement rules, isolated SQLite billing
state, a Stripe gateway, idempotent webhook processing, a durable usage outbox,
authenticated API routes, and a React billing workspace. Acceptance requires
unit, integration, executable Gherkin, production browser E2E, and mutation
tests.

## Red

Tests are introduced before implementation for local-free behavior, hosted
entitlements, checkout and portal creation, signature rejection, webhook replay
and ordering, usage deduplication and retry, grading/billing separation, typed
client transport, accessible subscription states, and the complete hosted
billing workflow.

The first focused runs failed during collection because the billing contracts,
repository, service, Stripe gateway, API routes, and dashboard component did not
exist. This established the increment boundary before production code was
added.

## Green

The smallest complete vertical slice added:

- fail-closed hosted configuration and free-by-default local behavior;
- SQLite billing accounts, webhook-event ledger, and usage outbox;
- server-owned Stripe Checkout and Customer Portal sessions;
- raw-body signed webhook handling with replay and ordering protection;
- active/trialing access checks on automated and PDF grading creation;
- retry-safe Stripe meter delivery using the durable usage UUID; and
- a typed, accessible Billing & usage dashboard.

## Refactor

Stripe request shapes were isolated behind a narrow gateway, pure status and
quantity rules moved into `billing_contract.py`, and persistence remained
separate from the grading repositories. The API-key fingerprint was extended to
96 bits because it now scopes a financial tenant. Webhook normalization supports
both legacy top-level and current item-level subscription period timestamps,
rejects subscriptions for any Price other than the configured metered Price,
and prevents duplicate Checkout for an existing subscription.

## Validate

- Python unit, integration, and executable Gherkin suite: `134 passed`.
- React unit/integration suite: `44 passed`; lint and TypeScript checks passed.
- Production Next.js build and browser Gherkin suite: `5 passed`.
- Browser visual verification: billing route loaded without console errors,
  runtime overlays, or horizontal overflow.
- Python mutation suite: `232/234` killed (`99.15%`); every MVP 6 contract
  mutant was killed. The two survivors are equivalent pre-existing MVP 4
  floating-point rounding mutations.
- Frontend mutation suite: `191/191` killed (`100%`).
- Dependency checks: Python requirements are consistent and `npm audit`
  reported zero vulnerabilities.
