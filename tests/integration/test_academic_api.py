from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from opengrader.api import create_app
from opengrader.api_models import ApiSettings
from opengrader.config import load_assignment

pytestmark = pytest.mark.integration


def settings(tmp_path: Path) -> ApiSettings:
    return ApiSettings(
        database_path=tmp_path / "jobs.db",
        output_root=tmp_path / "reports",
        pdf_storage_root=tmp_path / "pdfs",
        assignment_storage_root=tmp_path / "assignments",
        api_keys=("professor-key",),
        poll_interval=0.01,
    )


def payload(*, kind: str = "automated") -> dict[str, object]:
    value: dict[str, object] = {
        "name": "Accessible web profile",
        "kind": kind,
        "context": {
            "institution": "Open Learning Institute",
            "course_code": "WEB-110",
            "course_name": "Web Foundations",
            "period": "2026–2027",
            "section": "Section 2",
        },
    }
    if kind == "automated":
        value["automated"] = {
            "image": "python:3.12-slim",
            "timeout_seconds": 8,
            "memory_mb": 128,
            "cpus": 1,
            "pids_limit": 64,
            "tests": [
                {
                    "name": "Required files",
                    "command": "test -f index.html",
                    "points": 3,
                }
            ],
        }
    return value


def pdf_bytes() -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(output)
    return output.getvalue()


def test_professor_creates_filters_and_launches_a_visual_assignment(tmp_path) -> None:
    headers = {"Authorization": "Bearer professor-key"}
    application = create_app(settings(tmp_path))
    with TestClient(application) as client:
        created = client.post("/v1/assignments", json=payload(), headers=headers)
        assignment_id = created.json()["id"]
        listed = client.get(
            "/v1/assignments?institution=Open%20Learning%20Institute&section=Section%202",
            headers=headers,
        )
        launched = client.post(
            f"/v1/assignments/{assignment_id}/jobs",
            json={
                "submissions_dir": str(tmp_path / "submissions"),
                "no_docker": True,
                "workers": 2,
                "retries": 1,
                "submission_patterns": [],
            },
            headers=headers,
        )

    assert created.status_code == 201
    assert created.json()["context"]["course_code"] == "WEB-110"
    assert [item["id"] for item in listed.json()] == [assignment_id]
    assert launched.status_code == 202
    generated_path = Path(launched.json()["request"]["assignment_file"])
    assert generated_path.parent == tmp_path / "assignments"
    assert load_assignment(generated_path).name == "Accessible web profile"


def test_pdf_assignment_cannot_launch_an_automated_job(tmp_path) -> None:
    headers = {"Authorization": "Bearer professor-key"}
    with TestClient(create_app(settings(tmp_path))) as client:
        created = client.post(
            "/v1/assignments", json=payload(kind="pdf"), headers=headers
        )
        response = client.post(
            f"/v1/assignments/{created.json()['id']}/jobs",
            json={"submissions_dir": str(tmp_path / "submissions")},
            headers=headers,
        )

    assert response.status_code == 409
    assert "automated" in response.json()["detail"]


def test_pdf_submissions_can_be_organized_under_a_saved_assignment(tmp_path) -> None:
    headers = {"Authorization": "Bearer professor-key"}
    with TestClient(create_app(settings(tmp_path))) as client:
        assignment = client.post(
            "/v1/assignments", json=payload(kind="pdf"), headers=headers
        ).json()
        uploaded = client.post(
            "/v1/pdf-submissions",
            data={
                "student_id": "student-4",
                "title": "Accessible web profile",
                "assignment_id": assignment["id"],
            },
            files={"file": ("profile.pdf", pdf_bytes(), "application/pdf")},
            headers=headers,
        )
        listed = client.get(
            f"/v1/pdf-submissions?assignment_id={assignment['id']}",
            headers=headers,
        )

    assert uploaded.status_code == 201
    assert uploaded.json()["assignment_id"] == assignment["id"]
    assert [item["id"] for item in listed.json()] == [uploaded.json()["id"]]
