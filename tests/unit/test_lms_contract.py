import pytest
from pydantic import ValidationError

from opengrader.lms import (
    GradeSyncRequest,
    LmsAssignmentImport,
    StudentIdType,
    canvas_user_reference,
    grade_percentage,
)


def test_canvas_user_references_support_native_sis_and_login_identifiers() -> None:
    assert canvas_user_reference("42", StudentIdType.CANVAS_USER_ID) == "42"
    assert canvas_user_reference("X", StudentIdType.CANVAS_USER_ID) == "X"
    assert canvas_user_reference("S-100", StudentIdType.SIS_USER_ID) == "sis_user_id:S-100"
    assert canvas_user_reference("teacher@example.edu", StudentIdType.LOGIN_ID) == "sis_login_id:teacher@example.edu"


@pytest.mark.parametrize("student_id", ["", "  ", "a/b", "a?b", "a#b"])
def test_canvas_user_references_reject_blank_or_path_like_values(student_id: str) -> None:
    with pytest.raises(
        ValueError,
        match="^student identifiers must be nonblank path-safe values$",
    ):
        canvas_user_reference(student_id, StudentIdType.CANVAS_USER_ID)


def test_grade_percentage_is_bounded_and_stable() -> None:
    assert grade_percentage(8.555555, 10) == "85.5556%"
    assert grade_percentage(10, 10) == "100%"
    assert grade_percentage(1, 1) == "100%"
    assert grade_percentage(0, 10) == "0%"
    assert grade_percentage(0.0123445, 1) == "1.2345%"
    with pytest.raises(
        ValueError,
        match="^score must be between zero and the maximum$",
    ):
        grade_percentage(11, 10)
    with pytest.raises(
        ValueError,
        match="^score must be between zero and the maximum$",
    ):
        grade_percentage(-1, 10)
    with pytest.raises(ValueError, match="^maximum score must be positive$"):
        grade_percentage(1, 0)
    with pytest.raises(ValueError, match="^maximum score must be positive$"):
        grade_percentage(1, -1)


def test_import_and_grade_sync_contracts_fail_closed() -> None:
    with pytest.raises(ValidationError):
        LmsAssignmentImport.model_validate({
            "external_course_id": "course-1",
            "external_assignment_id": "assignment-1",
            "kind": "automated",
            "context": {
                "institution": "North College",
                "course_code": "CS-101",
                "course_name": "Programming",
                "period": "Fall 2026",
                "section": "A",
            },
        })

    with pytest.raises(ValidationError):
        GradeSyncRequest(job_id="job-1", student_id_type="unknown")
