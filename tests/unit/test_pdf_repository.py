import pytest

from opengrader.pdf_grading import (
    PdfAnnotation,
    PdfGradeRequest,
    PdfSubmissionStatus,
    RubricCriterion,
    RubricScore,
)
from opengrader.pdf_repository import PdfSubmissionRepository

pytestmark = pytest.mark.unit


def grade(*, finalized: bool) -> PdfGradeRequest:
    return PdfGradeRequest(
        rubric=[RubricCriterion(id="analysis", title="Analysis", max_points=10)],
        scores=[RubricScore(criterion_id="analysis", points=8, feedback="Good")],
        annotations=[PdfAnnotation(page=1, x=0.2, y=0.3, comment="Clarify")],
        overall_feedback="Well structured.",
        finalized=finalized,
    )


def test_pdf_submission_grading_is_durable_audited_and_finalization_is_immutable(
    tmp_path,
) -> None:
    repository = PdfSubmissionRepository(tmp_path / "jobs.db")
    repository.initialize()
    created = repository.create_submission(
        submission_id="pdf-123",
        student_id="alice",
        title="Research paper",
        original_filename="paper.pdf",
        size_bytes=512,
        sha256="a" * 64,
        page_count=2,
        actor="key:abc",
    )

    assert created.status is PdfSubmissionStatus.DRAFT
    assert created.grade is None
    draft = repository.save_grade("pdf-123", grade=grade(finalized=False), actor="key:abc")
    finalized = repository.save_grade("pdf-123", grade=grade(finalized=True), actor="key:abc")

    assert draft.status is PdfSubmissionStatus.DRAFT
    assert finalized.status is PdfSubmissionStatus.FINALIZED
    assert finalized.finalized_at is not None
    assert finalized.grade is not None and finalized.grade.total_score == 8
    with pytest.raises(ValueError, match="^Finalized PDF grades cannot be changed$"):
        repository.save_grade("pdf-123", grade=grade(finalized=False), actor="key:abc")

    reopened = PdfSubmissionRepository(tmp_path / "jobs.db")
    reopened.initialize()
    stored = reopened.get_submission("pdf-123")
    assert stored == finalized
    assert [item.id for item in reopened.list_submissions()] == ["pdf-123"]
    assert [event.action for event in reopened.list_audit_events()] == [
        "pdf_submission.created",
        "pdf_submission.grade_saved",
        "pdf_submission.finalized",
    ]
    assert all(
        event.resource_type == "pdf_submission"
        for event in reopened.list_audit_events()
    )


def test_pdf_repository_returns_none_for_missing_records_and_validates_pages(tmp_path) -> None:
    repository = PdfSubmissionRepository(tmp_path / "jobs.db")
    repository.initialize()

    assert repository.get_submission("missing") is None
    with pytest.raises(ValueError, match="^page_count must be positive$"):
        repository.create_submission(
            submission_id="bad",
            student_id="alice",
            title="Bad",
            original_filename="bad.pdf",
            size_bytes=1,
            sha256="b" * 64,
            page_count=0,
            actor="key:abc",
        )
