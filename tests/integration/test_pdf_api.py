from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter

from opengrader.api import create_app
from opengrader.api_models import ApiSettings

pytestmark = pytest.mark.integration


def pdf_bytes(*, pages: int = 1) -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    writer.write(output)
    return output.getvalue()


def settings(tmp_path: Path, *, max_bytes: int = 1_000_000) -> ApiSettings:
    return ApiSettings(
        database_path=tmp_path / "jobs.db",
        output_root=tmp_path / "reports",
        pdf_storage_root=tmp_path / "pdfs",
        pdf_max_upload_bytes=max_bytes,
        pdf_max_pages=5,
        api_keys=("valid-key",),
        poll_interval=0.01,
    )


def upload(client: TestClient, content: bytes, filename: str = "paper.pdf"):
    return client.post(
        "/v1/pdf-submissions",
        data={"student_id": "alice", "title": "Research paper"},
        files={"file": (filename, content, "application/pdf")},
        headers={"Authorization": "Bearer valid-key"},
    )


def test_authenticated_pdf_grading_workflow_persists_and_exports_feedback(tmp_path) -> None:
    headers = {"Authorization": "Bearer valid-key"}
    with TestClient(create_app(settings(tmp_path))) as client:
        uploaded = upload(client, pdf_bytes(pages=2), filename="../paper.pdf")
        assert uploaded.status_code == 201, uploaded.text
        submission = uploaded.json()
        submission_id = submission["id"]
        assert submission["student_id"] == "alice"
        assert submission["original_filename"] == "paper.pdf"
        assert submission["page_count"] == 2
        assert submission["status"] == "draft"
        assert submission["sha256"]

        listed = client.get("/v1/pdf-submissions", headers=headers)
        original = client.get(
            f"/v1/pdf-submissions/{submission_id}/document", headers=headers
        )
        assert [item["id"] for item in listed.json()] == [submission_id]
        assert original.status_code == 200
        assert original.headers["content-type"] == "application/pdf"
        assert original.content == pdf_bytes(pages=2)

        grade = client.put(
            f"/v1/pdf-submissions/{submission_id}/grade",
            json={
                "rubric": [
                    {"id": "argument", "title": "Argument", "max_points": 10}
                ],
                "scores": [
                    {
                        "criterion_id": "argument",
                        "points": 8.5,
                        "feedback": "Strong claim",
                    }
                ],
                "annotations": [
                    {"page": 2, "x": 0.2, "y": 0.3, "comment": "Add a citation"}
                ],
                "overall_feedback": "Good work.",
                "finalized": True,
            },
            headers=headers,
        )
        assert grade.status_code == 200, grade.text
        assert grade.json()["status"] == "finalized"
        assert grade.json()["total_score"] == 8.5
        assert grade.json()["maximum_points"] == 10

        feedback = client.get(
            f"/v1/pdf-submissions/{submission_id}/feedback.pdf", headers=headers
        )
        audit = client.get("/v1/audit-events", headers=headers)

    assert feedback.status_code == 200
    exported = PdfReader(BytesIO(feedback.content))
    assert exported.pages[1]["/Annots"][0].get_object()["/Contents"] == "Add a citation"
    assert "opengrader-feedback.json" in exported.attachments
    assert [event["action"] for event in audit.json()] == [
        "pdf_submission.created",
        "pdf_submission.finalized",
    ]


def test_pdf_upload_rejects_malformed_oversized_and_non_pdf_files(tmp_path) -> None:
    with TestClient(create_app(settings(tmp_path, max_bytes=100))) as client:
        malformed = upload(client, b"%PDF-this-is-not-valid")
        oversized = upload(client, b"x" * 101)
        wrong_extension = upload(client, pdf_bytes(), filename="paper.txt")

    assert malformed.status_code == 400
    assert malformed.json() == {"detail": "The uploaded file is not a valid PDF"}
    assert oversized.status_code == 413
    assert oversized.json() == {"detail": "PDF exceeds the 100 byte upload limit"}
    assert wrong_extension.status_code == 400
    assert wrong_extension.json() == {"detail": "Upload a file with a .pdf extension"}


def test_pdf_grade_rejects_out_of_range_pages_and_export_before_finalization(tmp_path) -> None:
    headers = {"Authorization": "Bearer valid-key"}
    with TestClient(create_app(settings(tmp_path))) as client:
        submission_id = upload(client, pdf_bytes()).json()["id"]
        invalid_grade = client.put(
            f"/v1/pdf-submissions/{submission_id}/grade",
            json={
                "rubric": [{"id": "a", "title": "A", "max_points": 1}],
                "scores": [{"criterion_id": "a", "points": 1}],
                "annotations": [
                    {"page": 2, "x": 0.5, "y": 0.5, "comment": "Outside"}
                ],
            },
            headers=headers,
        )
        unavailable = client.get(
            f"/v1/pdf-submissions/{submission_id}/feedback.pdf", headers=headers
        )

    assert invalid_grade.status_code == 422
    assert invalid_grade.json() == {
        "detail": "Annotation page 2 exceeds document page count 1"
    }
    assert unavailable.status_code == 409
    assert unavailable.json() == {"detail": "Finalize the grade before exporting feedback"}
