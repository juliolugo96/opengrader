from __future__ import annotations

from io import BytesIO
from pathlib import Path
from time import monotonic, sleep

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pytest_bdd import given, scenarios, then, when

from opengrader.api import create_app
from opengrader.api_models import ApiSettings

pytestmark = pytest.mark.e2e
scenarios("../features/similarity_review.feature")


def blank_pdf() -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(output)
    return output.getvalue()


@pytest.fixture
def similarity_world(tmp_path: Path):
    texts = {
        "alice": "The coastal habitat declines when plastic blocks sunlight and harms marine organisms.",
        "bob": "Opening note. The coastal habitat declines when plastic blocks sunlight and harms marine organisms.",
    }
    settings = ApiSettings(
        database_path=tmp_path / "jobs.db",
        output_root=tmp_path / "reports",
        pdf_storage_root=tmp_path / "pdfs",
        assignment_storage_root=tmp_path / "assignments",
        api_keys=("similarity-key",),
        poll_interval=0.01,
    )
    application = create_app(
        settings,
        similarity_text_extractor=lambda record, path: texts[record.student_id],
    )
    context = TestClient(application)
    world = {"context": context, "client": context.__enter__(), "headers": {"Authorization": "Bearer similarity-key"}}
    yield world
    context.__exit__(None, None, None)


@given("a configured similarity review API")
def configured_api(similarity_world):
    assert similarity_world["client"].get("/health").status_code == 200


@given("a written assignment with two similar PDF submissions")
def assignment_and_submissions(similarity_world):
    client, headers = similarity_world["client"], similarity_world["headers"]
    response = client.post(
        "/v1/assignments",
        headers=headers,
        json={
            "name": "Coastal systems essay",
            "kind": "pdf",
            "context": {"institution": "Northstar", "course_code": "BIO-201", "course_name": "Ecology", "period": "Spring 2027", "section": "A"},
            "automated": None,
        },
    )
    similarity_world["assignment_id"] = response.json()["id"]
    for student in ("alice", "bob"):
        uploaded = client.post(
            "/v1/pdf-submissions",
            headers=headers,
            data={"student_id": student, "title": f"{student} essay", "assignment_id": similarity_world["assignment_id"]},
            files={"file": (f"{student}.pdf", blank_pdf(), "application/pdf")},
        )
        assert uploaded.status_code == 201, uploaded.text


@when("I start an assignment similarity review")
def start_review(similarity_world):
    response = similarity_world["client"].post(
        "/v1/similarity/jobs",
        headers=similarity_world["headers"],
        json={"assignment_id": similarity_world["assignment_id"], "policy": {"ngram_size": 4, "window_size": 2, "min_shared_fingerprints": 1, "review_threshold": 0.1}},
    )
    assert response.status_code == 202, response.text
    similarity_world["job_id"] = response.json()["id"]


@then("the review completes with explainable evidence")
def completed_review(similarity_world):
    deadline = monotonic() + 3
    while monotonic() < deadline:
        response = similarity_world["client"].get(f"/v1/similarity/jobs/{similarity_world['job_id']}", headers=similarity_world["headers"])
        if response.json()["status"] in {"succeeded", "failed"}:
            break
        sleep(0.01)
    assert response.json()["status"] == "succeeded", response.text
    report = similarity_world["client"].get(f"/v1/similarity/jobs/{similarity_world['job_id']}/report", headers=similarity_world["headers"])
    assert report.status_code == 200
    assert report.json()["matches"][0]["evidence"]
    assert "misconduct" in report.json()["disclaimer"].lower()


@then("the review remains available as an immutable report")
def report_remains(similarity_world):
    first = similarity_world["client"].get(f"/v1/similarity/jobs/{similarity_world['job_id']}/report", headers=similarity_world["headers"]).json()
    second = similarity_world["client"].get(f"/v1/similarity/jobs/{similarity_world['job_id']}/report", headers=similarity_world["headers"]).json()
    assert first == second


@then("the similarity workflow appears in the audit trail")
def audit_trail(similarity_world):
    events = similarity_world["client"].get("/v1/audit-events", headers=similarity_world["headers"]).json()
    actions = [event["action"] for event in events]
    assert "similarity_job.created" in actions
    assert "similarity_job.succeeded" in actions
