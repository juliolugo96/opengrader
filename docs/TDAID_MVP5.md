# TDAID Record — MVP 5 PDF Grading

## Plan

The increment is split into a pure validation/export domain, SQLite persistence,
authenticated API routes, and a React grading workspace. Acceptance requires
unit, integration, executable Gherkin, browser E2E, and mutation tests.

## Red

Tests are introduced before implementation for malformed and oversized files,
encrypted and excessive-page documents, rubric invariants, annotation bounds,
durable grading state, feedback export, binary proxying, and the complete
instructor workflow.

## Green

The smallest end-to-end slice introduced a PDF grading domain, a durable SQLite
repository, authenticated upload/grading/export routes, and a dashboard queue,
preview, rubric editor, annotation editor, finalization action, and feedback
download. Generated storage paths, strict parsing, bounded streaming, and
immutable final grades enforce the MVP contract.

## Refactor

Rubric, score, coordinate, and page-bound rules were extracted into the pure
`pdf_contract` module so they can be tested and mutated independently of I/O.
The client reuses one typed request layer for JSON, multipart, and blob
responses, while the Next.js proxy forwards request and response bytes without
text conversion. PDF writing uses unique temporary output paths and atomic
replacement, and preview object URLs are revoked when their component unmounts.

## Validate

Validation on 2026-08-18 completed successfully:

- 100 Python unit, integration, and executable Gherkin tests passed.
- 39 Vitest component, client, and proxy tests passed.
- 4 Playwright Gherkin scenarios passed against the production Next.js build,
  including upload, annotation, rubric scoring, and finalization.
- Python mutation testing killed 219 of 221 mutants (99.10%). The two survivors
  are pre-existing equivalent MVP 4 rounding mutations; all MVP 5 PDF contract
  mutants were killed.
- Frontend mutation testing killed 150 of 150 mutants (100%).
- TypeScript type checking, ESLint, the production build, and `npm audit` passed;
  the audit reported zero known vulnerabilities.
- A production-server browser verification confirmed the PDF queue renders
  without console errors, error overlays, or horizontal overflow.
