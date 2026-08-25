import pytest
from pydantic import ValidationError

from opengrader.similarity import (
    SimilarityBand,
    SimilarityDocument,
    SimilarityPolicy,
    SimilarityJobRecord,
    SimilarityJobRequest,
    SimilarityJobResponse,
    SimilarityJobStatus,
)
from opengrader.similarity_contract import Fingerprint, analyze_documents, normalize_text, winnow

pytestmark = pytest.mark.unit


def document(identifier: str, student: str, text: str) -> SimilarityDocument:
    return SimilarityDocument(submission_id=identifier, student_id=student, text=text)


def test_normalization_is_unicode_aware_and_stable() -> None:
    assert normalize_text("  Café\nCAFÉ  ") == "café café"
    assert normalize_text("ＡＢＣ") == "abc"


def test_winnowing_is_deterministic_and_validates_parameters() -> None:
    first = winnow("one two three four five six seven", ngram_size=3, window_size=2)
    second = winnow("one two three four five six seven", ngram_size=3, window_size=2)
    assert first == second
    assert first
    with pytest.raises(ValueError, match="ngram_size"):
        winnow("text", ngram_size=0, window_size=2)
    with pytest.raises(ValueError, match="window_size"):
        winnow("text", ngram_size=1, window_size=0)


def test_winnowing_preserves_exact_boundaries_and_versioned_hashes() -> None:
    assert winnow("one", ngram_size=1, window_size=1) == (
        Fingerprint(
            value=4247950314234961152,
            token_start=0,
            token_end=1,
            char_start=0,
            char_end=3,
        ),
    )
    assert winnow("one two three", ngram_size=3, window_size=1) == (
        Fingerprint(
            value=2969746701289841019,
            token_start=0,
            token_end=3,
            char_start=0,
            char_end=13,
        ),
    )
    assert winnow("one two three four five", ngram_size=2, window_size=2) == (
        Fingerprint(14537296328239613283, 0, 2, 0, 7),
        Fingerprint(5382912499707859095, 2, 4, 8, 18),
    )


def test_policy_rejects_inverted_review_thresholds() -> None:
    with pytest.raises(ValidationError, match="high_signal_threshold"):
        SimilarityPolicy(review_threshold=0.8, high_signal_threshold=0.5)


def test_analysis_returns_explainable_review_matches_without_a_verdict() -> None:
    shared = (
        "The river ecosystem changes when fertilizer enters the water because "
        "algae consume oxygen and reduce habitat for fish populations."
    )
    report = analyze_documents(
        assignment_id="essay-1",
        job_id="job-1",
        documents=[
            document("a", "alice", f"Introduction. {shared} Final observation."),
            document("b", "bob", f"Different opening. {shared} A distinct conclusion."),
            document("c", "carol", "Volcanic rocks cool at different rates underground."),
        ],
        policy=SimilarityPolicy(
            ngram_size=4,
            window_size=2,
            min_shared_fingerprints=2,
            review_threshold=0.2,
            high_signal_threshold=0.9,
        ),
    )

    assert report.corpus_size == 3
    assert report.candidate_pairs_evaluated == 1
    assert len(report.matches) == 1
    match = report.matches[0]
    assert {match.left_submission_id, match.right_submission_id} == {"a", "b"}
    assert match.band is SimilarityBand.REVIEW
    assert match.evidence
    assert "fertilizer" in match.evidence[0].left_excerpt
    assert "misconduct" in report.disclaimer.lower()
    assert not hasattr(match, "verdict")


def test_analysis_skips_same_student_and_caps_candidate_work() -> None:
    text = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    report = analyze_documents(
        assignment_id="essay-2",
        job_id="job-2",
        documents=[
            document("a1", "alice", text),
            document("a2", "alice", text),
            document("b", "bob", text),
            document("c", "carol", text),
        ],
        policy=SimilarityPolicy(
            ngram_size=3,
            window_size=2,
            min_shared_fingerprints=1,
            max_candidate_pairs=1,
        ),
    )
    assert report.candidate_pairs_evaluated == 1
    assert len(report.matches) == 1
    pair = report.matches[0]
    assert pair.left_student_id != pair.right_student_id
    assert any("candidate limit" in warning.lower() for warning in report.warnings)


def test_short_documents_are_reported_as_indeterminate() -> None:
    report = analyze_documents(
        assignment_id="essay-3",
        job_id="job-3",
        documents=[document("a", "alice", "short"), document("b", "bob", "short")],
        policy=SimilarityPolicy(ngram_size=5, window_size=2),
    )
    assert report.matches == []
    assert report.indeterminate_documents == ["a", "b"]
    assert report.corpus_size == 2
    assert report.candidate_pairs_evaluated == 0
    assert report.warnings == [
        "Some documents were too short or contained too little extractable text for structural comparison."
    ]


def test_analysis_metrics_evidence_and_limits_are_exact() -> None:
    report = analyze_documents(
        assignment_id="x",
        job_id="j",
        documents=[
            document("a", "alice", "zero one two three four five six seven eight nine ten eleven twelve"),
            document("b", "bob", "prefix one two three four five six seven eight suffix"),
        ],
        policy=SimilarityPolicy(
            ngram_size=3,
            window_size=2,
            min_shared_fingerprints=1,
            review_threshold=0,
            high_signal_threshold=0.99,
            max_evidence_per_match=2,
        ),
    )
    assert report.model_dump(exclude={"generated_at"}) == {
        "job_id": "j",
        "assignment_id": "x",
        "algorithm_version": "structural-winnowing-v1",
        "corpus_size": 2,
        "candidate_pairs_evaluated": 1,
        "matches": [
            {
                "left_submission_id": "a",
                "left_student_id": "alice",
                "right_submission_id": "b",
                "right_student_id": "bob",
                "score": 0.746154,
                "containment": 0.833333,
                "jaccard": 0.625,
                "coverage": 0.615385,
                "band": SimilarityBand.REVIEW,
                "exact_match": False,
                "shared_fingerprints": 5,
                "evidence": [
                    {
                        "fingerprint": "2936a8e3f344e17b",
                        "left_excerpt": "zero one two three four five six seven eight nine ten eleven twelve",
                        "right_excerpt": "prefix one two three four five six seven eight suffix",
                        "left_start": 5,
                        "left_end": 18,
                        "right_start": 7,
                        "right_end": 20,
                    },
                    {
                        "fingerprint": "4e01cd5c2c3e8dd4",
                        "left_excerpt": "zero one two three four five six seven eight nine ten eleven twelve",
                        "right_excerpt": "prefix one two three four five six seven eight suffix",
                        "left_start": 19,
                        "left_end": 32,
                        "right_start": 21,
                        "right_end": 34,
                    },
                ],
            }
        ],
        "indeterminate_documents": [],
        "warnings": [],
        "disclaimer": "Similarity signals support instructor review; they do not determine plagiarism or academic misconduct.",
    }


def test_analysis_enforces_document_and_shared_fingerprint_boundaries() -> None:
    common = "one two three four five six"
    no_candidate = analyze_documents(
        assignment_id="x",
        job_id="j",
        documents=[document("a", "alice", common), document("b", "bob", common + " seven")],
        policy=SimilarityPolicy(ngram_size=4, window_size=3, min_shared_fingerprints=3),
    )
    assert no_candidate.candidate_pairs_evaluated == 0
    with pytest.raises(ValueError, match="limited to 2 documents"):
        analyze_documents(
            assignment_id="x",
            job_id="j",
            documents=[document(str(index), str(index), common) for index in range(3)],
            policy=SimilarityPolicy(max_documents=2),
        )


def test_analysis_marks_exact_nontrivial_text_as_high_signal() -> None:
    text = "one two three four five six seven eight"
    report = analyze_documents(
        assignment_id="x",
        job_id="j",
        documents=[document("a", "alice", text), document("b", "bob", text)],
        policy=SimilarityPolicy(ngram_size=3, window_size=2),
    )
    match = report.matches[0]
    assert (match.score, match.containment, match.jaccard, match.coverage) == (1, 1, 1, 0.875)
    assert match.exact_match is True
    assert match.band is SimilarityBand.HIGH_SIGNAL


def test_job_response_maps_every_public_state_field() -> None:
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    record = SimilarityJobRecord(
        id="job",
        assignment_id="essay",
        status=SimilarityJobStatus.FAILED,
        request=SimilarityJobRequest(assignment_id="essay"),
        submission_ids=["a", "b"],
        created_by="key:test",
        created_at=now,
        updated_at=now,
        started_at=now,
        completed_at=now,
        error="failed safely",
    )
    assert SimilarityJobResponse.from_record(record).model_dump() == {
        "id": "job",
        "assignment_id": "essay",
        "status": SimilarityJobStatus.FAILED,
        "request": record.request.model_dump(),
        "submission_count": 2,
        "created_by": "key:test",
        "created_at": now,
        "updated_at": now,
        "started_at": now,
        "completed_at": now,
        "error": "failed safely",
    }
