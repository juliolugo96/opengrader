from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from opengrader.api import create_app
from opengrader.api_models import ApiSettings

pytestmark = pytest.mark.integration


def settings(tmp_path: Path) -> ApiSettings:
    return ApiSettings(
        database_path=tmp_path / "jobs.db",
        output_root=tmp_path / "reports",
        pdf_storage_root=tmp_path / "pdfs",
        assignment_storage_root=tmp_path / "assignments",
        api_keys=("valid-key",),
        poll_interval=0.01,
    )


def assignment_payload(kind: str = "pdf") -> dict[str, object]:
    return {
        "name": "Essay",
        "kind": kind,
        "context": {"institution": "Northstar", "course_code": "WRIT-101", "course_name": "Writing", "period": "Fall 2027", "section": "A"},
        "automated": None if kind == "pdf" else {"tests": [{"name": "check", "command": "true", "points": 1}]},
    }


def test_similarity_routes_require_authentication_and_written_assignment_corpus(tmp_path) -> None:
    headers = {"Authorization": "Bearer valid-key"}
    with TestClient(create_app(settings(tmp_path))) as client:
        assert client.get("/v1/similarity/jobs").status_code == 401
        missing = client.post("/v1/similarity/jobs", headers=headers, json={"assignment_id": "missing"})
        automated = client.post("/v1/assignments", headers=headers, json=assignment_payload("automated")).json()
        wrong_kind = client.post("/v1/similarity/jobs", headers=headers, json={"assignment_id": automated["id"]})
        written = client.post("/v1/assignments", headers=headers, json=assignment_payload()).json()
        too_few = client.post("/v1/similarity/jobs", headers=headers, json={"assignment_id": written["id"]})
        absent_report = client.get("/v1/similarity/jobs/not-found/report", headers=headers)

    assert missing.status_code == 404
    assert wrong_kind.status_code == 409
    assert "written/PDF" in wrong_kind.json()["detail"]
    assert too_few.status_code == 409
    assert "At least two" in too_few.json()["detail"]
    assert absent_report.status_code == 404


def test_similarity_request_rejects_unknown_policy_fields(tmp_path) -> None:
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post(
            "/v1/similarity/jobs",
            headers={"Authorization": "Bearer valid-key"},
            json={"assignment_id": "essay", "policy": {"automatic_guilt": True}},
        )
    assert response.status_code == 422
