from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter
from pytest_bdd import given, scenarios, then, when

from opengrader.api import create_app
from opengrader.api_models import ApiSettings

pytestmark = pytest.mark.e2e
scenarios("../features/pdf_grading.feature")


@pytest.fixture
def pdf_world(tmp_path: Path):
    settings = ApiSettings(
        database_path=tmp_path / "jobs.db",
        output_root=tmp_path / "reports",
        pdf_storage_root=tmp_path / "pdfs",
        api_keys=("pdf-test-key",),
        poll_interval=0.01,
    )
    world = {
        "headers": {"Authorization": "Bearer pdf-test-key"},
        "context": TestClient(create_app(settings)),
    }
    world["client"] = world["context"].__enter__()
    yield world
    world["context"].__exit__(None, None, None)


@given("a configured PDF grading API")
def configured_pdf_api(pdf_world):
    assert pdf_world["client"].get("/health").status_code == 200


@given("a valid two-page PDF submission")
def valid_pdf_submission(pdf_world):
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    writer.write(output)
    pdf_world["pdf"] = output.getvalue()


@when("I upload the PDF for manual grading")
def upload_pdf(pdf_world):
    pdf_world["response"] = pdf_world["client"].post(
        "/v1/pdf-submissions",
        data={"student_id": "alice", "title": "Final essay"},
        files={"file": ("essay.pdf", pdf_world["pdf"], "application/pdf")},
        headers=pdf_world["headers"],
    )


@then("the PDF is accepted as a draft")
def accepted_as_draft(pdf_world):
    response = pdf_world["response"]
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["status"] == "draft"
    assert payload["page_count"] == 2
    pdf_world["submission_id"] = payload["id"]


@when("I finalize a rubric grade with a page annotation")
def finalize_pdf_grade(pdf_world):
    pdf_world["grade_response"] = pdf_world["client"].put(
        f"/v1/pdf-submissions/{pdf_world['submission_id']}/grade",
        json={
            "rubric": [{"id": "analysis", "title": "Analysis", "max_points": 10}],
            "scores": [{"criterion_id": "analysis", "points": 8.5, "feedback": "Strong"}],
            "annotations": [{"page": 2, "x": 0.25, "y": 0.4, "comment": "Add a citation"}],
            "overall_feedback": "Good work.",
            "finalized": True,
        },
        headers=pdf_world["headers"],
    )


@then("the finalized PDF grade reports the rubric total")
def finalized_total(pdf_world):
    response = pdf_world["grade_response"]
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "finalized"
    assert response.json()["total_score"] == 8.5
    assert response.json()["maximum_points"] == 10


@then("the feedback PDF preserves the page comment and structured feedback")
def exported_feedback(pdf_world):
    response = pdf_world["client"].get(
        f"/v1/pdf-submissions/{pdf_world['submission_id']}/feedback.pdf",
        headers=pdf_world["headers"],
    )
    assert response.status_code == 200
    reader = PdfReader(BytesIO(response.content))
    assert reader.pages[1]["/Annots"][0].get_object()["/Contents"] == "Add a citation"
    assert b'"overall_feedback":"Good work."' in reader.attachments[
        "opengrader-feedback.json"
    ][0]


@then("the PDF workflow appears in the audit trail")
def pdf_audit_trail(pdf_world):
    response = pdf_world["client"].get(
        "/v1/audit-events", headers=pdf_world["headers"]
    )
    assert [event["action"] for event in response.json()] == [
        "pdf_submission.created",
        "pdf_submission.finalized",
    ]
    assert all(event["resource_type"] == "pdf_submission" for event in response.json())
