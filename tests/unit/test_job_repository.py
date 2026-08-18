from datetime import UTC, datetime
from pathlib import Path

import pytest

from opengrader.api_models import ApiJobRequest, JobStatus
from opengrader.repository import JobRepository
from opengrader.results import GradingResult

pytestmark = pytest.mark.unit


def request() -> ApiJobRequest:
    return ApiJobRequest(
        assignment_file=Path("assignment.yaml"),
        submissions_dir=Path("submissions"),
        no_docker=True,
        workers=2,
        retries=1,
        submission_patterns=["a*"],
    )


def test_job_lifecycle_persists_result_reports_and_audit(tmp_path: Path) -> None:
    repository = JobRepository(tmp_path / "jobs.db")
    repository.initialize()

    queued = repository.create_job(request(), actor="key:abc")
    running = repository.claim_next_job(worker_actor="worker:test")
    assert running is not None
    assert running.id == queued.id
    assert running.status is JobStatus.RUNNING

    result = GradingResult(
        assignment="API",
        generated_at=datetime.now(UTC),
        runner="local",
        workers=2,
        retries=1,
        submissions=[],
    )
    repository.complete_job(
        queued.id,
        result=result,
        reports={"json": "/reports/results.json", "csv": "/reports/results.csv"},
        worker_actor="worker:test",
    )

    reopened = JobRepository(tmp_path / "jobs.db")
    reopened.initialize()
    stored = reopened.get_job(queued.id)
    assert stored is not None
    assert stored.status is JobStatus.SUCCEEDED
    assert stored.request == request()
    assert stored.result == result
    assert stored.reports["csv"] == "/reports/results.csv"
    assert stored.started_at is not None
    assert stored.completed_at is not None
    assert [event.action for event in reopened.list_audit_events()] == [
        "job.created",
        "job.started",
        "job.succeeded",
    ]


def test_initialize_requeues_interrupted_running_jobs(tmp_path: Path) -> None:
    repository = JobRepository(tmp_path / "jobs.db")
    repository.initialize()
    queued = repository.create_job(request(), actor="key:abc")
    assert repository.claim_next_job(worker_actor="worker:old") is not None

    recovered = JobRepository(tmp_path / "jobs.db")
    assert recovered.initialize() == 1
    job = recovered.get_job(queued.id)

    assert job is not None
    assert job.status is JobStatus.QUEUED
    assert job.started_at is None
    assert [event.action for event in recovered.list_audit_events()][-1] == "job.requeued"


def test_claim_is_fifo_and_status_filter_is_applied(tmp_path: Path) -> None:
    repository = JobRepository(tmp_path / "jobs.db")
    repository.initialize()
    first = repository.create_job(request(), actor="key:one")
    second = repository.create_job(request(), actor="key:two")

    claimed = repository.claim_next_job(worker_actor="worker:test")

    assert claimed is not None and claimed.id == first.id
    assert [job.id for job in repository.list_jobs(status=JobStatus.QUEUED)] == [second.id]
    assert [job.id for job in repository.list_jobs(status=JobStatus.RUNNING)] == [first.id]


def test_job_listing_supports_stable_offset_pagination(tmp_path: Path) -> None:
    repository = JobRepository(tmp_path / "jobs.db")
    repository.initialize()
    created = [repository.create_job(request(), actor=f"key:{index}") for index in range(3)]

    first_page = repository.list_jobs(limit=2, offset=0)
    second_page = repository.list_jobs(limit=2, offset=2)

    assert [job.id for job in first_page] == [created[2].id, created[1].id]
    assert [job.id for job in second_page] == [created[0].id]


def test_failure_is_terminal_and_missing_job_returns_none(tmp_path: Path) -> None:
    repository = JobRepository(tmp_path / "jobs.db")
    repository.initialize()
    job = repository.create_job(request(), actor="key:abc")
    repository.claim_next_job(worker_actor="worker:test")

    repository.fail_job(job.id, error="bad assignment", worker_actor="worker:test")

    failed = repository.get_job(job.id)
    assert failed is not None
    assert failed.status is JobStatus.FAILED
    assert failed.error == "bad assignment"
    assert repository.claim_next_job(worker_actor="worker:test") is None
    assert repository.get_job("missing") is None
