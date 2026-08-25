# Similarity Review Design

## Product boundary

OpenGrader provides assignment-scoped structural similarity evidence for an
instructor. It does not decide whether plagiarism or academic misconduct
occurred. Reports deliberately use `review` and `high_signal` bands rather than
verdicts, and the interface keeps the human-review notice beside the evidence.

The first implementation analyzes PDF submissions already attached to one
written assignment. This fits the existing professor workspace and avoids a
second ingestion, identity, or course model.

## Adapted architecture

The larger cloud concept separates ingestion, extraction, indexing, candidate
retrieval, comparison, reporting, and audit services. OpenGrader preserves those
contracts in a local-first topology:

```text
professor dashboard / authenticated API
                    |
           similarity application service
             /              \
 assignment + PDF stores   durable SQLite job repository
                                   |
                         managed local worker thread
                          /                    \
                 PDF text extractor     structural-winnowing-v1
                                               |
                                      immutable evidence report
```

The current worker is in-process, SQLite is the durable job and report store,
and PDF files remain in the configured PDF storage root. No broker, vector
database, search cluster, or container platform is required to run Community
edition.

## Analysis contract

`structural-winnowing-v1` performs:

1. bounded text extraction;
2. Unicode NFKC normalization, case folding, and language-independent word
   tokenization;
3. stable BLAKE2b hashes over token n-grams;
4. right-most-minimum winnowing;
5. an inverted fingerprint index to retrieve candidate pairs;
6. bounded comparison using containment, Jaccard overlap, and token coverage;
7. short, position-linked evidence excerpts.

Candidate retrieval is not an unbounded all-pairs loop. The policy caps corpus
size, candidate pairs, document characters, and evidence items. Submissions
from the same student are not compared. Documents without enough extractable
tokens are listed as indeterminate rather than treated as clean or suspicious.

The job snapshots submission IDs and the complete policy at creation. A
successful report is immutable. Every created, started, succeeded, or failed
transition enters the shared audit ledger. Errors are bounded and document text
is not written to logs or audit details.

## API

All endpoints require the existing bearer authentication:

- `POST /v1/similarity/jobs` creates a review for `assignment_id` and an optional policy.
- `GET /v1/similarity/jobs` lists reviews and can filter by `assignment_id`.
- `GET /v1/similarity/jobs/{job_id}` returns durable state without the large report.
- `GET /v1/similarity/jobs/{job_id}/report` returns a successful immutable report.

Creating a review requires a written/PDF assignment and at least two associated
PDF submissions. A report conflict returns HTTP 409 while work is incomplete.

## Evolution seams

The document extractor and analyzer sit behind application-service boundaries.
Future implementations can add source-code tokenizers, boilerplate suppression,
semantic candidate retrieval, or a distributed worker without changing the
professor workflow or report semantics. A hosted topology can project the same
job states onto object storage, a message bus, relational metadata, and vector
or search indexes.

Before semantic analysis is enabled, OpenGrader will require explicit embedding
model/version fields, tenant and assignment corpus filters, evaluation datasets,
cost limits, and privacy policy controls. Cross-assignment, cross-institution,
or global matching is not silently enabled by this design.
