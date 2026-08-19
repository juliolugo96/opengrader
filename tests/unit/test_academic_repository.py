from pathlib import Path

import pytest

from opengrader.academic import (
    AcademicAssignmentCreate,
    AcademicContext,
    AssignmentKind,
    AutomatedAssignmentDefinition,
)
from opengrader.academic_repository import AcademicAssignmentRepository

pytestmark = pytest.mark.unit


def automated_request(name: str = "Programming fundamentals") -> AcademicAssignmentCreate:
    return AcademicAssignmentCreate(
        name=name,
        kind=AssignmentKind.AUTOMATED,
        context=AcademicContext(
            institution="North College",
            course_code="CS-101",
            course_name="Introduction to Computing",
            period="2026 Fall",
            section="Section A",
        ),
        automated=AutomatedAssignmentDefinition(
            tests=[{"name": "Program runs", "command": "python solution.py"}]
        ),
    )


def test_assignment_catalog_groups_and_filters_academic_context(tmp_path: Path) -> None:
    repository = AcademicAssignmentRepository(tmp_path / "jobs.db")
    repository.initialize()
    first = repository.create(automated_request(), actor="key:professor")
    repository.create(
        AcademicAssignmentCreate(
            name="Primary source analysis",
            kind=AssignmentKind.PDF,
            context=AcademicContext(
                institution="North College",
                course_code="HIS-204",
                course_name="Modern History",
                period="2026 Fall",
                section="Evening",
            ),
        ),
        actor="key:professor",
    )

    matches = repository.list(institution="North College", course_code="CS-101")

    assert [record.id for record in matches] == [first.id]
    assert matches[0].context.section == "Section A"
    assert matches[0].automated is not None
    assert matches[0].automated.tests[0].points == 1


def test_assignment_catalog_updates_and_deletes_records(tmp_path: Path) -> None:
    repository = AcademicAssignmentRepository(tmp_path / "jobs.db")
    repository.initialize()
    created = repository.create(automated_request(), actor="key:professor")
    updated_request = automated_request("Computational thinking")

    updated = repository.update(
        created.id, updated_request, actor="key:professor"
    )

    assert updated.name == "Computational thinking"
    assert repository.delete(created.id, actor="key:professor") is True
    assert repository.get(created.id) is None
    assert repository.delete(created.id, actor="key:professor") is False


def test_assignment_kind_requires_the_matching_grading_definition() -> None:
    with pytest.raises(ValueError, match="automated"):
        AcademicAssignmentCreate(
            name="Missing checks",
            kind=AssignmentKind.AUTOMATED,
            context=AcademicContext(
                institution="North College",
                course_code="CS-101",
                course_name="Introduction to Computing",
                period="2026 Fall",
                section="A",
            ),
        )

    with pytest.raises(ValueError, match="PDF"):
        AcademicAssignmentCreate(
            name="Essay",
            kind=AssignmentKind.PDF,
            context=AcademicContext(
                institution="North College",
                course_code="HIS-204",
                course_name="Modern History",
                period="2026 Fall",
                section="Evening",
            ),
            automated=AutomatedAssignmentDefinition(
                tests=[{"name": "Unexpected", "command": "true"}]
            ),
        )
