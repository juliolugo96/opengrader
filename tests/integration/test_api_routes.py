from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from opengrader.api import create_app
from opengrader.api_models import ApiSettings

pytestmark = pytest.mark.integration


def settings(tmp_path: Path, *keys: str) -> ApiSettings:
    return ApiSettings(
        database_path=tmp_path / "jobs.db",
        output_root=tmp_path / "reports",
        api_keys=keys,
        poll_interval=0.01,
    )


def test_health_is_public_and_reports_auth_readiness(tmp_path: Path) -> None:
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["authentication_configured"] is False


def test_protected_routes_fail_closed_when_keys_are_unconfigured(tmp_path: Path) -> None:
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.get("/v1/jobs")

    assert response.status_code == 503
    assert response.json() == {"detail": "API authentication is not configured"}


@pytest.mark.parametrize(
    "authorization",
    [None, "Bearer wrong-key", "Basic valid-key"],
)
def test_missing_or_invalid_credentials_return_bearer_challenge(
    tmp_path: Path, authorization: str | None
) -> None:
    headers = {"Authorization": authorization} if authorization else {}
    with TestClient(create_app(settings(tmp_path, "valid-key"))) as client:
        response = client.get("/v1/jobs", headers=headers)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"detail": "Invalid or missing API key"}


def test_unknown_job_and_result_return_not_found(tmp_path: Path) -> None:
    headers = {"Authorization": "Bearer valid-key"}
    with TestClient(create_app(settings(tmp_path, "valid-key"))) as client:
        job_response = client.get("/v1/jobs/missing", headers=headers)
        result_response = client.get("/v1/jobs/missing/result", headers=headers)

    assert job_response.status_code == 404
    assert result_response.status_code == 404


def test_invalid_request_and_query_bounds_do_not_create_jobs(tmp_path: Path) -> None:
    headers = {"Authorization": "Bearer valid-key"}
    with TestClient(create_app(settings(tmp_path, "valid-key"))) as client:
        invalid_request = client.post(
            "/v1/jobs",
            json={
                "assignment_file": "assignment.yaml",
                "submissions_dir": "submissions",
                "workers": 0,
            },
            headers=headers,
        )
        invalid_limit = client.get("/v1/jobs?limit=101", headers=headers)
        jobs = client.get("/v1/jobs", headers=headers)

    assert invalid_request.status_code == 422
    assert invalid_limit.status_code == 422
    assert jobs.json() == []
