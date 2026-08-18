from io import BytesIO

import pytest
from pydantic import ValidationError
from pypdf import PdfReader, PdfWriter

from opengrader.pdf_grading import (
    PdfAnnotation,
    PdfGradeRequest,
    RubricCriterion,
    RubricScore,
    validate_pdf,
    write_feedback_pdf,
)

pytestmark = pytest.mark.unit


def pdf_bytes(*, pages: int = 1, encrypted: bool = False) -> bytes:
    output = BytesIO()
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    if encrypted:
        writer.encrypt("student-password")
    writer.write(output)
    return output.getvalue()


def grade_request(*, finalized: bool = False) -> PdfGradeRequest:
    return PdfGradeRequest(
        rubric=[
            RubricCriterion(
                id="argument", title="Argument", description="Clear thesis", max_points=6
            ),
            RubricCriterion(id="evidence", title="Evidence", max_points=4),
        ],
        scores=[
            RubricScore(criterion_id="argument", points=5.5, feedback="Strong thesis"),
            RubricScore(criterion_id="evidence", points=3, feedback="Add one source"),
        ],
        annotations=[
            PdfAnnotation(page=1, x=0.25, y=0.4, comment="Explain this transition")
        ],
        overall_feedback="Thoughtful work.",
        finalized=finalized,
    )


def test_pdf_validation_accepts_a_bounded_unencrypted_document(tmp_path) -> None:
    path = tmp_path / "submission.pdf"
    path.write_bytes(pdf_bytes(pages=2))

    metadata = validate_pdf(path, max_pages=5)

    assert metadata.page_count == 2


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"not a pdf", "The uploaded file is not a valid PDF"),
        (pdf_bytes(encrypted=True), "Encrypted PDFs are not supported"),
        (pdf_bytes(pages=3), "PDF exceeds the 2 page limit"),
    ],
)
def test_pdf_validation_rejects_unsafe_documents(tmp_path, content: bytes, message: str) -> None:
    path = tmp_path / "unsafe.pdf"
    path.write_bytes(content)

    with pytest.raises(ValueError, match=f"^{message}$"):
        validate_pdf(path, max_pages=2)


def test_grade_request_requires_unique_complete_bounded_rubric_scores() -> None:
    with pytest.raises(ValidationError, match="criterion IDs must be unique"):
        PdfGradeRequest(
            rubric=[
                RubricCriterion(id="same", title="One", max_points=2),
                RubricCriterion(id="same", title="Two", max_points=3),
            ],
            scores=[RubricScore(criterion_id="same", points=1)],
        )

    with pytest.raises(ValidationError, match="scores must match rubric criteria exactly"):
        PdfGradeRequest(
            rubric=[RubricCriterion(id="quality", title="Quality", max_points=2)],
            scores=[RubricScore(criterion_id="different", points=1)],
        )

    with pytest.raises(ValidationError, match="cannot exceed 2"):
        PdfGradeRequest(
            rubric=[RubricCriterion(id="quality", title="Quality", max_points=2)],
            scores=[RubricScore(criterion_id="quality", points=2.5)],
        )


def test_annotation_coordinates_are_normalized() -> None:
    with pytest.raises(ValidationError):
        PdfAnnotation(page=0, x=0.5, y=0.5, comment="bad page")
    with pytest.raises(ValidationError):
        PdfAnnotation(page=1, x=1.01, y=0.5, comment="bad x")
    with pytest.raises(ValidationError):
        PdfAnnotation(page=1, x=0.5, y=-0.01, comment="bad y")


def test_feedback_export_preserves_annotations_and_structured_feedback(tmp_path) -> None:
    source = tmp_path / "source.pdf"
    destination = tmp_path / "feedback.pdf"
    source.write_bytes(pdf_bytes())
    request = grade_request(finalized=True)

    write_feedback_pdf(source, destination, request)

    reader = PdfReader(destination)
    annotations = reader.pages[0]["/Annots"]
    assert len(annotations) == 1
    assert annotations[0].get_object()["/Contents"] == "Explain this transition"
    assert "opengrader-feedback.json" in reader.attachments
    attachment = reader.attachments["opengrader-feedback.json"][0]
    assert b'"total_score":8.5' in attachment
    assert b'"maximum_points":10.0' in attachment
