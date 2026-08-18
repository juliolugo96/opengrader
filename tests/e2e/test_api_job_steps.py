from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when

from opengrader.api import create_app
from opengrader.api_models import ApiSettings

pytestmark = pytest.mark.e2e
scenarios("../features/api_jobs.feature")


@pytest.fixture
def api_world(tmp_path: Path):
    settings = ApiSettings(
        database_path=tmp_path / "jobs.db",
        output_root=tmp_path / "reports",
        api_keys=("test-api-key",),
        poll_interval=0.01,
    )
    return {"settings": settings, "headers": {"Authorization": "Bearer test-api-key"}}


@given("a configured OpenGrader API")
def configured_api(api_world):
    app = create_app(api_world["settings"])
    client_context = TestClient(app)
    api_world["client_context"] = client_context
    api_world["client"] = client_context.__enter__()


@given("a passing local grading fixture")
def passing_fixture(api_world, tmp_path: Path):
    assignment = tmp_path / "assignment.yaml"
    assignment.write_text(
        "name: HTTP grading\ntests:\n  - name: works\n    command: python solution.py\n    points: 2\n",
        encoding="utf-8",
    )
    submission = tmp_path / "submissions" / "student-1"
    submission.mkdir(parents=True)
    (submission / "solution.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    api_world["request"] = {
        "assignment_path": str(assignment),
        "submissions_dir": str(submission.parent),
        "submission_filter": "student-*",
        "no_docker": True,
    }


@when("I submit a job without an API key")
def submit_unauthenticated(api_world):
    api_world["response"] = api_world["client"].post(
        "/v1/jobs",
        json={"assignment_file": "a.yaml", "submissions_dir": "submissions"},
    )


@when("I submit an authenticated local grading job")
def submit_authenticated(api_world):
    api_world["response"] = api_world["client"].post(
        "/v1/jobs", json=api_world["request"], headers=api_world["headers"]
    )


@then("the API responds with unauthorized")
def unauthorized(api_world):
    assert api_world["response"].status_code == 401
    api_world["client_context"].__exit__(None, None, None)


@then("the API accepts a queued job")
def accepted(api_world):
    response = api_world["response"]
    assert response.status_code == 202, response.text
    payload = response.json()
    assert payload["status"] in {"queued", "running"}
    api_world["job_id"] = payload["id"]


@then("the job eventually succeeds")
def eventually_succeeds(api_world):
    for _ in range(200):
        response = api_world["client"].get(
            f"/v1/jobs/{api_world['job_id']}", headers=api_world["headers"]
        )
        if response.json()["status"] == "succeeded":
            api_world["job"] = response.json()
            return
        time.sleep(0.01)
    pytest.fail(f"job did not succeed: {response.text}")


@then("I can retrieve its grading result")
def retrieve_result(api_world):
    response = api_world["client"].get(
        f"/v1/jobs/{api_world['job_id']}/result", headers=api_world["headers"]
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["assignment"] == "HTTP grading"
    assert payload["result"]["submissions"][0]["score"] == 2
    assert payload["statistics"] == {
        "total_score": 2,
        "maximum_points": 2,
        "student_count": 1,
    }
    assert set(payload["reports"]) == {"json", "markdown", "csv"}


@then("its lifecycle appears in the audit trail")
def lifecycle_audit(api_world):
    response = api_world["client"].get(
        "/v1/audit-events", headers=api_world["headers"]
    )
    actions = [event["action"] for event in response.json()]
    assert actions == ["job.created", "job.started", "job.succeeded"]


@then("the succeeded job survives an API restart")
def survives_restart(api_world):
    api_world["client_context"].__exit__(None, None, None)
    with TestClient(create_app(api_world["settings"])) as restarted:
        response = restarted.get(
            f"/v1/jobs/{api_world['job_id']}", headers=api_world["headers"]
        )
    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
