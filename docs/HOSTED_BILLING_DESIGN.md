# Hosted Billing Design

## Outcome

Hosted billing adds optional Stripe subscriptions and durable usage metering for hosted
deployments. Billing is disabled by default: the CLI and every local grading
feature remain free and do not require Stripe configuration.

## Contract

```text
authenticated API-key fingerprint
  -> isolated billing account
  -> hosted entitlement check (active or trialing)
  -> accepted automated job or PDF submission
  -> durable, uniquely keyed usage event
  -> background Stripe meter-event delivery

Stripe Checkout / Customer Portal
  -> signed raw-body webhook
  -> idempotent event ledger
  -> timestamp-ordered subscription projection
  -> hosted entitlement
```

- Billing tenants use the existing non-secret API-key fingerprint. Raw API keys
  are never stored in billing tables or sent to Stripe.
- Local mode is unlimited. Hosted mode returns HTTP `402` for new grading work
  unless the tenant is `active` or `trialing`.
- Subscription state is changed only by verified Stripe webhooks. Browser
  redirects never grant access.
- Webhook event IDs are unique, and older events cannot overwrite newer
  subscription state.
- Every accepted automated job and PDF submission is one grading usage unit.
  The grading record and billing event use separate tables joined only by an
  opaque resource identifier.
- Usage delivery uses a durable outbox and the usage-event UUID as Stripe's
  meter-event identifier, making retries idempotent.
- Stripe failures do not corrupt or delete accepted grading records. Failed
  usage deliveries remain pending for retry.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/v1/billing/overview` | Edition, subscription, and usage summary |
| `POST` | `/v1/billing/checkout` | Create hosted subscription Checkout |
| `POST` | `/v1/billing/portal` | Create a Stripe Customer Portal session |
| `POST` | `/v1/billing/webhook` | Verify and apply Stripe lifecycle events |

Checkout, portal, and overview routes require the existing bearer key. The
webhook route is public by necessity and requires a valid Stripe signature.

## State and failure boundaries

Billing has dedicated `billing_accounts`, `billing_usage_events`, and
`stripe_webhook_events` tables. Subscription projections retain the Stripe
event creation timestamp to tolerate out-of-order delivery. The usage worker is
single-process, matching the grading worker deployment constraint.

Supported lifecycle events are `checkout.session.completed` and
`customer.subscription.created`, `.updated`, and `.deleted`. Unknown verified
events are acknowledged and recorded so Stripe does not retry them forever.
