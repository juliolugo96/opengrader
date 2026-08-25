from datetime import UTC, datetime

import pytest

from opengrader.similarity import SimilarityJobRequest, SimilarityJobStatus, SimilarityReport
from opengrader.similarity_repository import SimilarityRepository

pytestmark = pytest.mark.unit


def test_repository_claims_recovers_and_keeps_reports_immutable(tmp_path) -> None:
    repository = SimilarityRepository(tmp_path / "jobs.db")
    assert repository.initialize() == 0
    created = repository.create(
        SimilarityJobRequest(assignment_id="essay-1"),
        submission_ids=["a", "b"],
        actor="key:test",
    )
    claimed = repository.claim_next(worker_actor="worker:test")
    assert claimed is not None
    assert claimed.id == created.id
    assert claimed.status is SimilarityJobStatus.RUNNING

    assert repository.initialize() == 1
    recovered = repository.claim_next(worker_actor="worker:test")
    assert recovered is not None
    report = SimilarityReport(
        job_id=recovered.id,
        assignment_id="essay-1",
        generated_at=datetime.now(UTC),
        corpus_size=2,
        candidate_pairs_evaluated=0,
    )
    completed = repository.complete(
        recovered.id, report=report, worker_actor="worker:test"
    )
    assert completed.status is SimilarityJobStatus.SUCCEEDED
    assert completed.report == report
    with pytest.raises(ValueError, match="already has a report"):
        repository.complete(recovered.id, report=report, worker_actor="worker:test")


def test_repository_filters_jobs_by_assignment(tmp_path) -> None:
    repository = SimilarityRepository(tmp_path / "jobs.db")
    repository.initialize()
    repository.create(SimilarityJobRequest(assignment_id="a"), submission_ids=["1", "2"], actor="key:test")
    repository.create(SimilarityJobRequest(assignment_id="b"), submission_ids=["3", "4"], actor="key:test")
    assert [job.assignment_id for job in repository.list(assignment_id="a")] == ["a"]
