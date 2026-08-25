# End-to-End Testing

OpenGrader uses two complementary end-to-end layers so fast product scenarios
remain deterministic while at least one browser journey crosses every real
platform boundary.

## Browser product scenarios

The Playwright Gherkin suite covers assignment authoring, job pagination,
results and exports, audit history, PDF grading, similarity evidence, billing,
Canvas workflows, and plan comparison. These scenarios use deterministic HTTP responses so interface
behavior and failure diagnosis remain stable.

## Full-platform persistence scenario

`platform.feature` exercises this complete path:

```text
browser form
  -> Next.js same-origin proxy
  -> authenticated FastAPI route
  -> academic assignment service
  -> temporary SQLite database and audit ledger
  -> API response
  -> React Query cache and rendered assignment
  -> browser reload and durable read
```

Playwright starts an isolated API on `127.0.0.1:8100`. The API uses a fresh
temporary directory for its database, assignment definitions, PDFs, and
reports. The directory is discarded when the test server stops, so local
operator data is never read or modified. The browser receives a dedicated test
credential through an initialization script and reaches the API through the
same proxy used by the product.

The scenario creates a written assignment, confirms the immediate response,
reloads the browser to prove the record came from durable storage, and opens
the audit screen to verify that the real creation event was recorded.

## Running the suite

From `client/`:

```sh
npm run test:e2e
```

This command builds the production Next.js application, prepares its standalone
assets, generates tests from the Gherkin features, starts both isolated servers,
and runs every Playwright scenario with one worker. Failed scenarios retain a
screenshot and trace under `client/test-results/`.

The Python `pytest -m e2e` suite separately covers complete CLI and API domain
journeys, including real PDF persistence and Canvas synchronization through a
controlled adapter. Run both suites in CI because they guard different seams.
