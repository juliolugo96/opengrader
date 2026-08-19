from pathlib import Path

import pytest
from pydantic import ValidationError

from opengrader.academic import (
    AcademicAssignmentCreate,
    AcademicAssignmentLaunch,
    AcademicContext,
    AssignmentKind,
    AutomatedAssignmentDefinition,
)
from opengrader.academic_repository import AcademicAssignmentRepository
from opengrader.academic_service import AcademicAssignmentService
from opengrader.config import load_assignment

pytestmark = pytest.mark.unit


def request(kind: AssignmentKind = AssignmentKind.AUTOMATED):
    return AcademicAssignmentCreate(
        name="  Data investigation  ",
        kind=kind,
        context=AcademicContext(
            institution="  Riverdale College  ",
            course_code=" STAT-201 ",
            course_name=" Applied Statistics ",
            period=" Fall 2026 ",
            section=" B ",
        ),
        automated=(
            AutomatedAssignmentDefinition(
                image=" python:3.12-slim ",
                setup="   ",
                tests=[{"name": "Analysis runs", "command": "python analysis.py"}],
            )
            if kind is AssignmentKind.AUTOMATED
            else None
        ),
    )


def service(tmp_path: Path):
    repository = AcademicAssignmentRepository(tmp_path / "jobs.db")
    repository.initialize()
    return AcademicAssignmentService(repository, storage_root=tmp_path / "definitions")


def test_contract_normalizes_professor_text_and_optional_setup() -> None:
    value = request()
    launch = AcademicAssignmentLaunch(submissions_dir=" submissions ")

    assert value.name == "Data investigation"
    assert value.context.model_dump() == {
        "institution": "Riverdale College",
        "course_code": "STAT-201",
        "course_name": "Applied Statistics",
        "period": "Fall 2026",
        "section": "B",
    }
    assert value.automated is not None
    assert value.automated.image == "python:3.12-slim"
    assert value.automated.setup is None
    assert launch.submissions_dir == "submissions"


@pytest.mark.parametrize(
    "field,value",
    [
        ("institution", " "),
        ("course_code", " "),
        ("course_name", " "),
        ("period", " "),
        ("section", " "),
    ],
)
def test_contract_rejects_blank_academic_dimensions(field: str, value: str) -> None:
    context = {
        "institution": "Riverdale College",
        "course_code": "STAT-201",
        "course_name": "Applied Statistics",
        "period": "Fall 2026",
        "section": "B",
        field: value,
    }
    with pytest.raises(ValidationError, match=field):
        AcademicContext(**context)


def test_contract_rejects_duplicate_evaluation_names() -> None:
    with pytest.raises(ValidationError, match="unique"):
        AutomatedAssignmentDefinition(
            tests=[
                {"name": "Same", "command": "true"},
                {"name": "Same", "command": "false"},
            ]
        )


def test_service_materializes_launch_and_removes_generated_definition(tmp_path: Path) -> None:
    academic_service = service(tmp_path)
    created = academic_service.create(request(), actor="key:professor")

    job = academic_service.job_request(
        created.id,
        AcademicAssignmentLaunch(
            submissions_dir="submissions",
            no_docker=True,
            workers=3,
            retries=2,
            submission_patterns=["section-*"]
        ),
    )

    assert job.submissions_dir == Path("submissions")
    assert job.no_docker is True
    assert job.workers == 3
    assert job.retries == 2
    assert job.submission_patterns == ["section-*"]
    assert load_assignment(job.assignment_file).name == "Data investigation"
    assert academic_service.delete(created.id, actor="key:professor") is True
    assert not job.assignment_file.exists()


def test_service_rejects_missing_and_written_assignment_launches(tmp_path: Path) -> None:
    academic_service = service(tmp_path)
    launch = AcademicAssignmentLaunch(submissions_dir="submissions")
    with pytest.raises(KeyError):
        academic_service.job_request("missing", launch)

    written = academic_service.create(request(AssignmentKind.PDF), actor="key:professor")
    with pytest.raises(ValueError, match="automated"):
        academic_service.job_request(written.id, launch)
    assert academic_service.delete("missing", actor="key:professor") is False
