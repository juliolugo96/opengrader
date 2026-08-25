# TDAID Record: Similarity Review

## Intent

Adapt the proposed plagiarism-detection architecture into the existing
local-first OpenGrader domain/service/repository/worker/API/dashboard patterns,
while preserving explainability, bounded work, auditability, algorithm
versioning, and human decision-making.

## Red

The first tests were written before the similarity modules existed. Collection
failed with `ModuleNotFoundError: No module named 'opengrader.similarity'`.

The contracts covered Unicode normalization, deterministic fingerprints,
validated thresholds, explainable evidence without a verdict, same-student
exclusion, candidate limits, indeterminate documents, restart recovery,
immutable completion, authentication, corpus validation, and complete Gherkin
workflows.

## Green

The smallest complete vertical slice added a pure analysis contract, domain
models, SQLite job/report repository, PDF-backed application service, managed
worker, authenticated endpoints, localized React Query dashboard, and unit,
integration, Python Gherkin E2E, and Playwright Gherkin coverage.

## Refactor and safeguards

Candidate generation uses an inverted fingerprint index and evaluates only
pairs meeting the shared-fingerprint rule. Policy bounds protect local
resources. Report bodies are excluded from job-list responses, errors are
bounded, and evidence excerpts are limited. Exact matches that are too short to
produce a fingerprint remain indeterminate.

## Mutation targets

The pure contract and its domain model are included in Python mutation
configuration. The instructor component is included in the client mutation
target set. Surviving mutants are reviewed for missing behavior assertions
before delivery.
