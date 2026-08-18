from pathlib import Path

import pytest
from pydantic import ValidationError

from opengrader.api_models import (
    ApiJobRequest,
    ApiSettings,
    JobStatus,
    ResultStatistics,
    api_key_id,
)
from opengrader.results import GradingResult, SubmissionResult, TestResult as GraderTestResult

pytestmark = pytest.mark.unit


def test_settings_load_paths_keys_and_poll_interval(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENGRADER_DATABASE", str(tmp_path / "jobs.db"))
    monkeypatch.setenv("OPENGRADER_OUTPUT_ROOT", str(tmp_path / "reports"))
    monkeypatch.setenv("OPENGRADER_API_KEYS", " first, second ,,first ")
    monkeypatch.setenv("OPENGRADER_POLL_INTERVAL", "0.25")

    settings = ApiSettings.from_env()

    assert settings.database_path == tmp_path / "jobs.db"
    assert settings.output_root == tmp_path / "reports"
    assert settings.api_keys == ("first", "second")
    assert settings.poll_interval == 0.25


def test_api_key_id_is_stable_and_does_not_reveal_key() -> None:
    identifier = api_key_id("super-secret")

    assert identifier == api_key_id("super-secret")
    assert len(identifier) == 12
    assert "secret" not in identifier


def test_job_request_defaults_to_docker_and_single_attempt() -> None:
    request = ApiJobRequest(
        assignment_file=Path("assignment.yaml"), submissions_dir=Path("submissions")
    )

    assert request.no_docker is False
    assert request.workers == 1
    assert request.retries == 0
    assert request.submission_patterns == []


def test_job_request_accepts_mvp4_documented_field_names() -> None:
    request = ApiJobRequest.model_validate(
        {
            "assignment_path": "assignments/hw1.yaml",
            "submissions_dir": "submissions",
            "submission_filter": "section-a-*",
        }
    )

    assert request.assignment_file == Path("assignments/hw1.yaml")
    assert request.submission_patterns == ["section-a-*"]


def test_result_statistics_round_floating_point_cohort_totals() -> None:
    submissions = [
        SubmissionResult(
            student_id=f"student-{index}",
            tests=[
                GraderTestResult(
                    name="score",
                    command="true",
                    passed=True,
                    points_earned=0.1,
                    points_possible=0.2,
                    exit_code=0,
                    duration_seconds=0.01,
                )
            ],
        )
        for index in range(3)
    ]
    result = GradingResult(
        assignment="Floating point",
        generated_at="2026-08-17T12:00:00Z",
        runner="local",
        submissions=submissions,
    )

    assert ResultStatistics.from_result(result).model_dump() == {
        "total_score": 0.3,
        "maximum_points": 0.6,
        "student_count": 3,
    }


@pytest.mark.parametrize(
    "field, value",
    [("workers", 0), ("workers", 65), ("retries", -1), ("retries", 11)],
)
def test_job_request_rejects_unsafe_batch_bounds(field: str, value: int) -> None:
    payload = {
        "assignment_file": "assignment.yaml",
        "submissions_dir": "submissions",
        field: value,
    }

    with pytest.raises(ValidationError):
        ApiJobRequest.model_validate(payload)


def test_job_status_has_only_documented_states() -> None:
    assert [status.value for status in JobStatus] == [
        "queued",
        "running",
        "succeeded",
        "failed",
    ]
