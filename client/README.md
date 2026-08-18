# OpenGrader Console

The MVP 4 dashboard is an isolated Next.js application for the OpenGrader API.
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
Playwright against an isolated production server on port 3100. `test:mutation`
runs Stryker against critical API pagination, export, and result-metric logic
and enforces a minimum mutation score.

The server-side catch-all proxy exists to keep local browser requests same-origin
without enabling permissive CORS on the grading API. It forwards only the
request body, content type, and bearer header, rejects embedded URL credentials,
uses a host allowlist, disables redirects and caching, and applies a 30-second
timeout.
