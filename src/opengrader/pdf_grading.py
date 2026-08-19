"""Validation and feedback-export rules for manual PDF grading."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Text
from pypdf.errors import PdfReadError

from opengrader.pdf_contract import annotation_rect, rubric_totals, validate_rubric_scores


class RubricCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,49}$")
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1_000)
    max_points: Annotated[float, Field(gt=0, le=1_000)]


class RubricScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,49}$")
    points: Annotated[float, Field(ge=0, le=1_000)]
    feedback: str = Field(default="", max_length=2_000)


class PdfAnnotation(BaseModel):
    """A page comment at a normalized top-left coordinate."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    page: int = Field(ge=1)
    x: Annotated[float, Field(ge=0, le=1)]
    y: Annotated[float, Field(ge=0, le=1)]
    comment: str = Field(min_length=1, max_length=2_000)


class PdfGradeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rubric: list[RubricCriterion] = Field(min_length=1, max_length=50)
    scores: list[RubricScore] = Field(min_length=1, max_length=50)
    annotations: list[PdfAnnotation] = Field(default_factory=list, max_length=500)
    overall_feedback: str = Field(default="", max_length=5_000)
    finalized: bool = False

    @model_validator(mode="after")
    def validate_rubric_scores(self) -> Self:
        validate_rubric_scores(self.rubric, self.scores)
        return self

    @property
    def total_score(self) -> float:
        return rubric_totals(self.rubric, self.scores)[0]

    @property
    def maximum_points(self) -> float:
        return rubric_totals(self.rubric, self.scores)[1]


class PdfSubmissionStatus(StrEnum):
    DRAFT = "draft"
    FINALIZED = "finalized"


class PdfSubmissionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    assignment_id: str | None = None
    student_id: str
    title: str
    original_filename: str
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    page_count: int = Field(ge=1)
    status: PdfSubmissionStatus
    grade: PdfGradeRequest | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    finalized_at: datetime | None = None

    @computed_field
    @property
    def total_score(self) -> float:
        return self.grade.total_score if self.grade is not None else 0

    @computed_field
    @property
    def maximum_points(self) -> float:
        return self.grade.maximum_points if self.grade is not None else 0


@dataclass(frozen=True, slots=True)
class PdfMetadata:
    page_count: int


def validate_pdf(path: Path, *, max_pages: int) -> PdfMetadata:
    """Strictly parse a PDF and enforce encryption and page-count boundaries."""

    if max_pages < 1:
        raise ValueError("max_pages must be positive")
    try:
        reader = PdfReader(path, strict=True)
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported")
        page_count = len(reader.pages)
        if page_count < 1:
            raise ValueError("PDF must contain at least one page")
        if page_count > max_pages:
            raise ValueError(f"PDF exceeds the {max_pages} page limit")
        for page in reader.pages:
            float(page.mediabox.width)
            float(page.mediabox.height)
    except ValueError:
        raise
    except (PdfReadError, OSError, TypeError, KeyError) as exc:
        raise ValueError("The uploaded file is not a valid PDF") from exc
    return PdfMetadata(page_count=page_count)


def write_feedback_pdf(
    source: Path, destination: Path, grade: PdfGradeRequest
) -> None:
    """Write printable page comments and attach the complete feedback payload."""

    reader = PdfReader(source, strict=True)
    writer = PdfWriter(clone_from=reader)
    for annotation in grade.annotations:
        if annotation.page > len(writer.pages):
            raise ValueError(
                f"annotation page {annotation.page} exceeds document page count"
            )
        page = writer.pages[annotation.page - 1]
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        writer.add_annotation(
            page_number=annotation.page - 1,
            annotation=Text(
                rect=annotation_rect(
                    x=annotation.x, y=annotation.y, width=width, height=height
                ),
                text=annotation.comment,
                open=False,
                flags=4,
            ),
        )

    payload = {
        **grade.model_dump(mode="json"),
        "total_score": grade.total_score,
        "maximum_points": grade.maximum_points,
    }
    writer.add_attachment(
        "opengrader-feedback.json",
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(),
    )
    writer.add_metadata(
        {
            "/Subject": (
                f"OpenGrader feedback: {grade.total_score:g}/"
                f"{grade.maximum_points:g} points"
            )
        }
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4()}.tmp")
    try:
        with temporary.open("wb") as output:
            writer.write(output)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
