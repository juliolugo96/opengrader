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
```

The server-side catch-all proxy exists to keep local browser requests same-origin
without enabling permissive CORS on the grading API. It forwards only the
request body, content type, and bearer header, rejects embedded URL credentials,
uses a host allowlist, disables redirects and caching, and applies a 30-second
timeout.
