# OpenGrader Console

The operations dashboard is an isolated Next.js application for the OpenGrader API.
It stores its API URL, bearer key, and theme in versioned browser localStorage.

## Development

Requirements: Node.js 20.9 or newer and a running OpenGrader API.

```sh
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000/settings`, configure the API URL and key, then test
the connection. The default proxy allowlist accepts only `localhost` and
`127.0.0.1`; set `OPENGRADER_ALLOWED_HOSTS` for another explicitly trusted API
hostname.

## Checks

```sh
npm run typecheck
npm run lint
npm test
npm run build
npm run test:e2e
npm run test:mutation
```

`test:e2e` builds the dashboard and executes its Gherkin scenarios through
Playwright against an isolated production server on port 3100. It also starts a
real OpenGrader API on port 8100 with temporary SQLite storage for the browser →
proxy → API → persistence → browser scenario. See the
[end-to-end testing guide](../docs/E2E_TESTING.md). `test:mutation` runs Stryker
against critical API pagination, export, and result-metric logic and enforces a
minimum mutation score.

The server-side catch-all proxy exists to keep local browser requests same-origin
without enabling permissive CORS on the grading API. It forwards only the
request body, content type, and bearer header, rejects embedded URL credentials,
uses a host allowlist, disables redirects and caching, and applies a 30-second
timeout.

## PDF grading

`/pdf` lists durable PDF submissions and provides a multipart upload form.
`/pdf/[id]` fetches the protected original document as a blob for preview,
keeps rubric and annotation editing in the browser, and sends one validated
grade payload to the API. After finalization the workspace becomes read-only
and exposes the annotated feedback PDF download.

## Billing and usage

`/billing` makes the local-free boundary explicit when server billing is off.
In hosted mode it renders Stripe subscription status, renewal or cancellation
timing, accepted/reported/pending usage units, Checkout email validation, and a
Customer Portal action. The browser supplies only the billing email; Price IDs,
return URLs, customer binding, and entitlement decisions stay server-owned.

## LMS integrations and plans

`/integrations` discovers Canvas courses and assignments through the API,
imports or links academic work, and previews or submits grades. No Canvas token
is accepted by the browser. `/plans` gives a localized, explicit comparison of
Community, Hosted early access, and Institution/design-partner scope; roadmap
items are labeled as planned.
