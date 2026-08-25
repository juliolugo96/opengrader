"""Pure, versioned structural similarity analysis primitives."""

from __future__ import annotations

import hashlib
import itertools
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from opengrader.similarity import (
    SimilarityBand,
    SimilarityDocument,
    SimilarityEvidence,
    SimilarityMatch,
    SimilarityPolicy,
    SimilarityReport,
)

_TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class Token:
    value: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class Fingerprint:
    value: int
    token_start: int
    token_end: int
    char_start: int
    char_end: int


@dataclass(frozen=True, slots=True)
class _Features:
    document: SimilarityDocument
    normalized: str
    tokens: tuple[Token, ...]
    fingerprints: tuple[Fingerprint, ...]
    by_hash: dict[int, Fingerprint]
    exact_hash: str


def normalize_text(text: str) -> str:
    """Return a language-independent comparison form without stemming semantics."""

    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def winnow(text: str, *, ngram_size: int, window_size: int) -> tuple[Fingerprint, ...]:
    if ngram_size < 1:
        raise ValueError("ngram_size must be positive")
    if window_size < 1:
        raise ValueError("window_size must be positive")
    normalized = normalize_text(text)
    tokens = tuple(
        Token(match.group(), match.start(), match.end())
        for match in _TOKEN_PATTERN.finditer(normalized)
    )
    if len(tokens) < ngram_size:
        return ()
    hashes = [
        _stable_hash("\x1f".join(token.value for token in tokens[index : index + ngram_size]))
        for index in range(len(tokens) - ngram_size + 1)
    ]
    effective_window = min(window_size, len(hashes))
    selected: list[int] = []
    for start in range(len(hashes) - effective_window + 1):
        window = hashes[start : start + effective_window]
        minimum = min(window)
        position = start + max(
            index for index, value in enumerate(window) if value == minimum
        )
        if not selected or selected[-1] != position:
            selected.append(position)
    return tuple(
        Fingerprint(
            value=hashes[position],
            token_start=position,
            token_end=position + ngram_size,
            char_start=tokens[position].start,
            char_end=tokens[position + ngram_size - 1].end,
        )
        for position in selected
    )


def analyze_documents(
    *,
    assignment_id: str,
    job_id: str,
    documents: list[SimilarityDocument],
    policy: SimilarityPolicy,
) -> SimilarityReport:
    if len(documents) > policy.max_documents:
        raise ValueError(f"Similarity review is limited to {policy.max_documents} documents")

    features = [_features(document, policy) for document in documents]
    indeterminate = [
        item.document.submission_id for item in features if not item.fingerprints
    ]
    postings: dict[int, list[int]] = defaultdict(list)
    for index, item in enumerate(features):
        for value in item.by_hash:
            postings[value].append(index)

    shared_counts: Counter[tuple[int, int]] = Counter()
    for indexes in postings.values():
        for left, right in itertools.combinations(indexes, 2):
            if features[left].document.student_id != features[right].document.student_id:
                shared_counts[(left, right)] += 1

    exact_pairs: set[tuple[int, int]] = set()
    exact_groups: dict[str, list[int]] = defaultdict(list)
    for index, item in enumerate(features):
        if item.fingerprints:
            exact_groups[item.exact_hash].append(index)
    for indexes in exact_groups.values():
        for left, right in itertools.combinations(indexes, 2):
            if features[left].document.student_id != features[right].document.student_id:
                exact_pairs.add((left, right))

    candidates = {
        pair
        for pair, count in shared_counts.items()
        if count >= policy.min_shared_fingerprints
    } | exact_pairs
    ranked = sorted(
        candidates,
        key=lambda pair: (-shared_counts[pair], pair[0], pair[1]),
    )
    warnings: list[str] = []
    if len(ranked) > policy.max_candidate_pairs:
        warnings.append(
            f"Candidate limit reached; evaluated the strongest {policy.max_candidate_pairs} pairs."
        )
        ranked = ranked[: policy.max_candidate_pairs]

    matches = [
        match
        for pair in ranked
        if (match := _compare(features[pair[0]], features[pair[1]], policy))
        is not None
    ]
    matches.sort(key=lambda match: (-match.score, match.left_submission_id, match.right_submission_id))
    if indeterminate:
        warnings.append(
            "Some documents were too short or contained too little extractable text for structural comparison."
        )
    return SimilarityReport(
        job_id=job_id,
        assignment_id=assignment_id,
        generated_at=datetime.now(UTC),
        corpus_size=len(documents),
        candidate_pairs_evaluated=len(ranked),
        matches=matches,
        indeterminate_documents=sorted(indeterminate),
        warnings=warnings,
    )


def _features(document: SimilarityDocument, policy: SimilarityPolicy) -> _Features:
    normalized = normalize_text(document.text[: policy.max_characters_per_document])
    tokens = tuple(
        Token(match.group(), match.start(), match.end())
        for match in _TOKEN_PATTERN.finditer(normalized)
    )
    fingerprints = winnow(
        normalized, ngram_size=policy.ngram_size, window_size=policy.window_size
    )
    by_hash: dict[int, Fingerprint] = {}
    for fingerprint in fingerprints:
        by_hash.setdefault(fingerprint.value, fingerprint)
    return _Features(
        document=document,
        normalized=normalized,
        tokens=tokens,
        fingerprints=fingerprints,
        by_hash=by_hash,
        exact_hash=hashlib.sha256(normalized.encode()).hexdigest(),
    )


def _compare(
    left: _Features, right: _Features, policy: SimilarityPolicy
) -> SimilarityMatch | None:
    left_hashes = set(left.by_hash)
    right_hashes = set(right.by_hash)
    shared = left_hashes & right_hashes
    exact = bool(left.normalized) and left.exact_hash == right.exact_hash
    containment = (
        len(shared) / min(len(left_hashes), len(right_hashes))
        if left_hashes and right_hashes
        else 0.0
    )
    union = left_hashes | right_hashes
    jaccard = len(shared) / len(union) if union else 0.0
    coverage = min(
        _coverage(left, shared),
        _coverage(right, shared),
    )
    score = 1.0 if exact else 0.6 * containment + 0.4 * coverage
    if not exact and score < policy.review_threshold:
        return None
    band = (
        SimilarityBand.HIGH_SIGNAL
        if exact or score >= policy.high_signal_threshold
        else SimilarityBand.REVIEW
    )
    return SimilarityMatch(
        left_submission_id=left.document.submission_id,
        left_student_id=left.document.student_id,
        right_submission_id=right.document.submission_id,
        right_student_id=right.document.student_id,
        score=round(score, 6),
        containment=round(containment, 6),
        jaccard=round(jaccard, 6),
        coverage=round(coverage, 6),
        band=band,
        exact_match=exact,
        shared_fingerprints=len(shared),
        evidence=_evidence(left, right, shared, policy.max_evidence_per_match),
    )


def _coverage(features: _Features, shared: set[int]) -> float:
    if not features.tokens:
        return 0.0
    covered: set[int] = set()
    for value in shared:
        fingerprint = features.by_hash[value]
        covered.update(range(fingerprint.token_start, fingerprint.token_end))
    return len(covered) / len(features.tokens)


def _evidence(
    left: _Features, right: _Features, shared: set[int], limit: int
) -> list[SimilarityEvidence]:
    evidence: list[SimilarityEvidence] = []
    previous_left_end = -1
    for value in sorted(shared, key=lambda item: left.by_hash[item].char_start):
        left_span = left.by_hash[value]
        right_span = right.by_hash[value]
        if left_span.char_start < previous_left_end:
            continue
        evidence.append(
            SimilarityEvidence(
                fingerprint=f"{value:016x}",
                left_excerpt=_excerpt(left.normalized, left_span.char_start, left_span.char_end),
                right_excerpt=_excerpt(right.normalized, right_span.char_start, right_span.char_end),
                left_start=left_span.char_start,
                left_end=left_span.char_end,
                right_start=right_span.char_start,
                right_end=right_span.char_end,
            )
        )
        previous_left_end = left_span.char_end
        if len(evidence) == limit:
            break
    return evidence


def _excerpt(text: str, start: int, end: int, context: int = 70) -> str:
    excerpt_start = max(0, start - context)
    excerpt_end = min(len(text), end + context)
    prefix = "…" if excerpt_start else ""
    suffix = "…" if excerpt_end < len(text) else ""
    return f"{prefix}{text[excerpt_start:excerpt_end]}{suffix}"


def _stable_hash(value: str) -> int:
    return int.from_bytes(
        hashlib.blake2b(
            value.encode(), digest_size=8, person=b"OpenGrade"
        ).digest(),
        "big",
    )
