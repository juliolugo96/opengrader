from pathlib import Path

import pytest
from pydantic import ValidationError

from opengrader.api_models import ApiJobRequest, ApiSettings, JobStatus, api_key_id

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
