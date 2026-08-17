from pathlib import Path

import pytest

from opengrader.api_models import ApiJobRequest, JobStatus
from opengrader.repository import JobRepository
from opengrader.runners import LocalRunner
from opengrader.worker import JobWorker

pytestmark = pytest.mark.integration


def test_worker_runs_real_pipeline_and_persists_reports(tmp_path: Path) -> None:
    assignment = tmp_path / "assignment.yaml"
    assignment.write_text(
        "name: API worker\ntests:\n  - name: run\n    command: python solution.py\n    points: 3\n",
        encoding="utf-8",
    )
    submission = tmp_path / "submissions" / "alice"
    submission.mkdir(parents=True)
    (submission / "solution.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    repository = JobRepository(tmp_path / "jobs.db")
    repository.initialize()
    job = repository.create_job(
        ApiJobRequest(
            assignment_file=assignment,
            submissions_dir=submission.parent,
            no_docker=True,
            workers=2,
        ),
        actor="key:test",
    )
    worker = JobWorker(
        repository,
        output_root=tmp_path / "reports",
        poll_interval=0.01,
        runner_factory=lambda no_docker: LocalRunner(),
        worker_actor="worker:integration",
    )

    assert worker.run_once() is True
    assert worker.run_once() is False

    stored = repository.get_job(job.id)
    assert stored is not None
    assert stored.status is JobStatus.SUCCEEDED
    assert stored.result is not None
    assert stored.result.submissions[0].score == 3
    assert set(stored.reports) == {"json", "markdown", "csv"}
    assert all(Path(path).is_file() for path in stored.reports.values())


def test_worker_persists_domain_failure_and_continues(tmp_path: Path) -> None:
    repository = JobRepository(tmp_path / "jobs.db")
    repository.initialize()
    job = repository.create_job(
        ApiJobRequest(
            assignment_file=tmp_path / "missing.yaml",
            submissions_dir=tmp_path / "missing-submissions",
            no_docker=True,
        ),
        actor="key:test",
    )
    worker = JobWorker(
        repository,
        output_root=tmp_path / "reports",
        runner_factory=lambda no_docker: LocalRunner(),
    )

    assert worker.run_once() is True
    stored = repository.get_job(job.id)
    assert stored is not None
    assert stored.status is JobStatus.FAILED
    assert "Could not read assignment file" in stored.error
    assert repository.list_audit_events()[-1].action == "job.failed"
