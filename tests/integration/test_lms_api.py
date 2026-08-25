from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from opengrader.api import create_app
from opengrader.api_models import ApiSettings
from opengrader.lms import (
    LmsAssignment,
    LmsConnectionStatus,
    LmsCourse,
    LmsProvider,
    StudentIdType,
)

pytestmark = pytest.mark.integration


class FakeCanvasAdapter:
    provider = LmsProvider.CANVAS

    def __init__(self) -> None:
        self.grades: list[dict[str, object]] = []

    def connection_status(self) -> LmsConnectionStatus:
        return LmsConnectionStatus(
            provider=self.provider,
            configured=True,
            account_name="Riverdale Canvas",
            base_url="https://canvas.example",
        )

    def list_courses(self) -> list[LmsCourse]:
        return [LmsCourse(id="7", name="Applied Statistics", course_code="STAT-201")]

    def list_assignments(self, course_id: str) -> list[LmsAssignment]:
        assert course_id == "7"
        return [self.get_assignment(course_id, "99")]

    def get_assignment(self, course_id: str, assignment_id: str) -> LmsAssignment:
        assert (course_id, assignment_id) == ("7", "99")
        return LmsAssignment(
            id="99", course_id="7", name="Population investigation",
            description="Submit a PDF report", points_possible=20,
            due_at=None, published=True, submission_types=["online_upload"],
        )

    def post_grade(self, **grade: object) -> None:
        self.grades.append(grade)


def _settings(tmp_path: Path) -> ApiSettings:
    return ApiSettings(
        database_path=tmp_path / "jobs.db",
        output_root=tmp_path / "reports",
        pdf_storage_root=tmp_path / "pdfs",
        assignment_storage_root=tmp_path / "assignments",
        canvas_base_url="https://canvas.example",
        canvas_access_token="secret-token",
        canvas_account_name="Riverdale Canvas",
        api_keys=("professor-key",),
        poll_interval=0.01,
    )


def _pdf_bytes() -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(output)
    return output.getvalue()


def _import_payload() -> dict[str, object]:
    return {
        "external_course_id": "7",
        "external_assignment_id": "99",
        "kind": "pdf",
        "context": {
            "institution": "Riverdale College",
            "course_code": "STAT-201",
            "course_name": "Applied Statistics",
            "period": "Fall 2026",
            "section": "B",
        },
    }


def test_canvas_discovery_import_link_and_idempotent_pdf_grade_sync(tmp_path: Path) -> None:
    adapter = FakeCanvasAdapter()
    headers = {"Authorization": "Bearer professor-key"}
    application = create_app(_settings(tmp_path), lms_adapters=(adapter,))
    with TestClient(application) as client:
        status = client.get("/v1/lms/providers", headers=headers)
        courses = client.get("/v1/lms/canvas/courses", headers=headers)
        assignments = client.get("/v1/lms/canvas/courses/7/assignments", headers=headers)
        imported = client.post(
            "/v1/lms/canvas/imports", json=_import_payload(), headers=headers
        )
        assignment_id = imported.json()["assignment"]["id"]
        uploaded = client.post(
            "/v1/pdf-submissions",
            data={
                "student_id": "S-100",
                "title": "Population investigation",
                "assignment_id": assignment_id,
            },
            files={"file": ("report.pdf", _pdf_bytes(), "application/pdf")},
            headers=headers,
        )
        draft_sync = client.post(
            f"/v1/lms/links/{assignment_id}/grades",
            json={"student_id_type": "sis_user_id", "dry_run": False},
            headers=headers,
        )
        grade = {
            "rubric": [{"id": "analysis", "title": "Analysis", "max_points": 20}],
            "scores": [{"criterion_id": "analysis", "points": 17, "feedback": "Clear"}],
            "annotations": [],
            "overall_feedback": "Good work",
            "finalized": True,
        }
        finalized = client.put(
            f"/v1/pdf-submissions/{uploaded.json()['id']}/grade",
            json=grade,
            headers=headers,
        )
        synced = client.post(
            f"/v1/lms/links/{assignment_id}/grades",
            json={"student_id_type": "sis_user_id", "dry_run": False},
            headers=headers,
        )
        replayed = client.post(
            f"/v1/lms/links/{assignment_id}/grades",
            json={"student_id_type": "sis_user_id", "dry_run": False},
            headers=headers,
        )

    assert status.json()[0]["configured"] is True
    assert courses.json()[0]["course_code"] == "STAT-201"
    assert assignments.json()[0]["id"] == "99"
    assert imported.status_code == 201
    assert imported.json()["link"]["external_assignment_id"] == "99"
    assert draft_sync.json()["attempted"] == 0
    assert finalized.json()["status"] == "finalized"
    assert synced.json()["sent"] == 1
    assert synced.json()["skipped"] == 0
    assert replayed.json()["sent"] == 0
    assert replayed.json()["skipped"] == 1
    assert len(adapter.grades) == 1
    assert adapter.grades[0]["posted_grade"] == "85%"
    assert adapter.grades[0]["student_id_type"] is StudentIdType.SIS_USER_ID


def test_lms_routes_fail_closed_when_provider_is_not_configured(tmp_path: Path) -> None:
    values = _settings(tmp_path)
    settings = ApiSettings(
        database_path=values.database_path,
        output_root=values.output_root,
        pdf_storage_root=values.pdf_storage_root,
        assignment_storage_root=values.assignment_storage_root,
        api_keys=values.api_keys,
        poll_interval=values.poll_interval,
    )
    with TestClient(create_app(settings)) as client:
        response = client.get(
            "/v1/lms/canvas/courses",
            headers={"Authorization": "Bearer professor-key"},
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "Canvas is not configured"}
