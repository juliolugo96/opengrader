from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pytest_bdd import given, scenarios, then, when

from opengrader.api import create_app
from opengrader.api_models import ApiSettings
from opengrader.lms import LmsAssignment, LmsConnectionStatus, LmsCourse, LmsProvider

pytestmark = pytest.mark.e2e
scenarios("../features/lms_integration.feature")


class CanvasWorldAdapter:
    provider = LmsProvider.CANVAS

    def __init__(self) -> None:
        self.grades: list[dict[str, object]] = []

    def connection_status(self):
        return LmsConnectionStatus(
            provider=self.provider, configured=True,
            account_name="Design Partner Canvas", base_url="https://canvas.example",
        )

    def list_courses(self):
        return [LmsCourse(id="7", name="World History", course_code="HIST-204")]

    def list_assignments(self, course_id: str):
        return [self.get_assignment(course_id, "99")]

    def get_assignment(self, course_id: str, assignment_id: str):
        return LmsAssignment(
            id=assignment_id, course_id=course_id, name="Primary source essay",
            description="Essay", points_possible=40, due_at=None, published=True,
            submission_types=["online_upload"],
        )

    def post_grade(self, **grade):
        self.grades.append(grade)


@pytest.fixture
def lms_world(tmp_path: Path):
    adapter = CanvasWorldAdapter()
    settings = ApiSettings(
        database_path=tmp_path / "jobs.db", output_root=tmp_path / "reports",
        pdf_storage_root=tmp_path / "pdfs", assignment_storage_root=tmp_path / "assignments",
        canvas_base_url="https://canvas.example", canvas_access_token="secret",
        api_keys=("lms-key",), poll_interval=0.01,
    )
    context = TestClient(create_app(settings, lms_adapters=(adapter,)))
    world = {
        "client": context.__enter__(), "context": context, "adapter": adapter,
        "headers": {"Authorization": "Bearer lms-key"},
    }
    yield world
    context.__exit__(None, None, None)


def one_page_pdf() -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(output)
    return output.getvalue()


@given("a configured Canvas integration")
def configured_canvas(lms_world):
    response = lms_world["client"].get("/v1/lms/providers", headers=lms_world["headers"])
    assert response.json()[0]["configured"] is True


@when("I import a Canvas assignment into a course section")
def import_assignment(lms_world):
    response = lms_world["client"].post(
        "/v1/lms/canvas/imports",
        json={
            "external_course_id": "7", "external_assignment_id": "99", "kind": "pdf",
            "context": {
                "institution": "Riverdale College", "course_code": "HIST-204",
                "course_name": "World History", "period": "Fall 2026", "section": "A",
            },
        },
        headers=lms_world["headers"],
    )
    assert response.status_code == 201, response.text
    lms_world["imported"] = response.json()


@then("the local assignment is linked to the Canvas assignment")
def linked_assignment(lms_world):
    links = lms_world["client"].get("/v1/lms/links", headers=lms_world["headers"])
    assert links.json()[0]["local_assignment_id"] == lms_world["imported"]["assignment"]["id"]


@when("I finalize a linked PDF grade")
def finalize_pdf_grade(lms_world):
    assignment = lms_world["imported"]["assignment"]
    upload = lms_world["client"].post(
        "/v1/pdf-submissions",
        data={"student_id": "S-200", "title": assignment["name"], "assignment_id": assignment["id"]},
        files={"file": ("essay.pdf", one_page_pdf(), "application/pdf")},
        headers=lms_world["headers"],
    ).json()
    response = lms_world["client"].put(
        f"/v1/pdf-submissions/{upload['id']}/grade",
        json={
            "rubric": [{"id": "argument", "title": "Argument", "max_points": 40}],
            "scores": [{"criterion_id": "argument", "points": 36, "feedback": "Strong"}],
            "annotations": [], "overall_feedback": "Strong essay", "finalized": True,
        },
        headers=lms_world["headers"],
    )
    assert response.status_code == 200


@when("I synchronize the assignment grades using SIS identifiers")
def sync_grades(lms_world):
    assignment_id = lms_world["imported"]["assignment"]["id"]
    lms_world["sync"] = lms_world["client"].post(
        f"/v1/lms/links/{assignment_id}/grades",
        json={"student_id_type": "sis_user_id"}, headers=lms_world["headers"],
    ).json()
    lms_world["replay"] = lms_world["client"].post(
        f"/v1/lms/links/{assignment_id}/grades",
        json={"student_id_type": "sis_user_id"}, headers=lms_world["headers"],
    ).json()


@then("Canvas receives the percentage grade once")
def canvas_receives_once(lms_world):
    assert lms_world["sync"]["sent"] == 1
    assert len(lms_world["adapter"].grades) == 1
    assert lms_world["adapter"].grades[0]["posted_grade"] == "90%"


@then("repeating the synchronization skips the delivered grade")
def repeated_sync_skips(lms_world):
    assert lms_world["replay"]["skipped"] == 1
