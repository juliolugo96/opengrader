from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pytest_bdd import given, scenarios, then, when

from opengrader.api import create_app
from opengrader.api_models import ApiSettings
from opengrader.config import load_assignment

pytestmark = pytest.mark.e2e
scenarios("../features/academic_workspace.feature")


@pytest.fixture
def academic_world(tmp_path: Path):
    settings = ApiSettings(
        database_path=tmp_path / "jobs.db",
        output_root=tmp_path / "reports",
        pdf_storage_root=tmp_path / "pdfs",
        assignment_storage_root=tmp_path / "assignments",
        api_keys=("professor-bdd-key",),
        poll_interval=0.01,
    )
    context = TestClient(create_app(settings))
    world = {
        "client": context.__enter__(),
        "context": context,
        "headers": {"Authorization": "Bearer professor-bdd-key"},
        "tmp_path": tmp_path,
    }
    yield world
    context.__exit__(None, None, None)


def assignment_payload(kind: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Population data investigation",
        "kind": kind,
        "context": {
            "institution": "Riverdale College",
            "course_code": "STAT-201",
            "course_name": "Applied Statistics",
            "period": "Fall 2026",
            "section": "B",
        },
    }
    if kind == "automated":
        payload["automated"] = {
            "image": "python:3.12-slim",
            "timeout_seconds": 10,
            "memory_mb": 256,
            "cpus": 1,
            "pids_limit": 128,
            "tests": [
                {"name": "Analysis runs", "command": "python analysis.py", "points": 20}
            ],
        }
    return payload


def one_page_pdf() -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(output)
    return output.getvalue()


@given("a configured professor assignment API")
def configured_assignment_api(academic_world):
    assert academic_world["client"].get("/health").status_code == 200


@when("I create an automated assignment for a course section")
def create_automated_assignment(academic_world):
    response = academic_world["client"].post(
        "/v1/assignments",
        json=assignment_payload("automated"),
        headers=academic_world["headers"],
    )
    assert response.status_code == 201, response.text
    academic_world["assignment"] = response.json()


@then("the assignment is stored with its institution, period, and section")
def assignment_has_academic_context(academic_world):
    listed = academic_world["client"].get(
        "/v1/assignments?institution=Riverdale%20College&period=Fall%202026&section=B",
        headers=academic_world["headers"],
    )
    assert [item["id"] for item in listed.json()] == [academic_world["assignment"]["id"]]


@when("I launch that saved assignment against a submissions folder")
def launch_saved_assignment(academic_world):
    academic_world["launched"] = academic_world["client"].post(
        f"/v1/assignments/{academic_world['assignment']['id']}/jobs",
        json={
            "submissions_dir": str(academic_world["tmp_path"] / "submissions"),
            "no_docker": True,
        },
        headers=academic_world["headers"],
    )


@then("OpenGrader creates a durable job from a generated definition")
def durable_job_uses_generated_definition(academic_world):
    response = academic_world["launched"]
    assert response.status_code == 202, response.text
    definition = Path(response.json()["request"]["assignment_file"])
    assert definition.parent == academic_world["tmp_path"] / "assignments"
    assert load_assignment(definition).name == "Population data investigation"


@when("I create a written assignment and upload a PDF submission")
def create_written_assignment_with_submission(academic_world):
    assignment = academic_world["client"].post(
        "/v1/assignments",
        json=assignment_payload("pdf"),
        headers=academic_world["headers"],
    ).json()
    uploaded = academic_world["client"].post(
        "/v1/pdf-submissions",
        data={
            "student_id": "student-42",
            "title": assignment["name"],
            "assignment_id": assignment["id"],
        },
        files={"file": ("investigation.pdf", one_page_pdf(), "application/pdf")},
        headers=academic_world["headers"],
    )
    assert uploaded.status_code == 201, uploaded.text
    academic_world["written_assignment"] = assignment
    academic_world["submission"] = uploaded.json()


@then("the PDF submission is listed under that assignment")
def submission_is_grouped(academic_world):
    listed = academic_world["client"].get(
        f"/v1/pdf-submissions?assignment_id={academic_world['written_assignment']['id']}",
        headers=academic_world["headers"],
    )
    assert [item["id"] for item in listed.json()] == [academic_world["submission"]["id"]]
