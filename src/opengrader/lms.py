"""Provider-neutral contracts for learning-management integrations."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from opengrader.academic import (
    AcademicAssignmentRecord,
    AcademicContext,
    AssignmentKind,
    AutomatedAssignmentDefinition,
)
from opengrader.lms_contract import (
    StudentIdType,
    canvas_user_reference,
    grade_percentage,
)


class LmsProvider(StrEnum):
    CANVAS = "canvas"


class LmsConnectionStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: LmsProvider
    configured: bool
    account_name: str | None = None
    base_url: str | None = None


class LmsCourse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=300)
    course_code: str = Field(default="", max_length=100)
    term: str | None = Field(default=None, max_length=160)


class LmsAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=200)
    course_id: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=20_000)
    points_possible: float | None = Field(default=None, ge=0, le=1_000_000)
    due_at: datetime | None = None
    published: bool = False
    submission_types: list[str] = Field(default_factory=list, max_length=50)


class LmsAssignmentImport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_course_id: str = Field(min_length=1, max_length=200)
    external_assignment_id: str = Field(min_length=1, max_length=200)
    kind: AssignmentKind = AssignmentKind.PDF
    context: AcademicContext
    automated: AutomatedAssignmentDefinition | None = None

    @field_validator("external_course_id", "external_assignment_id")
    @classmethod
    def normalize_external_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("external identifiers must not be blank")
        return normalized

    @model_validator(mode="after")
    def matching_definition(self) -> Self:
        if self.kind is AssignmentKind.AUTOMATED and self.automated is None:
            raise ValueError("automated imports require evaluation checks")
        if self.kind is AssignmentKind.PDF and self.automated is not None:
            raise ValueError("PDF imports cannot include automated checks")
        return self


class LmsAssignmentLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_assignment_id: str = Field(min_length=1, max_length=80)
    external_course_id: str = Field(min_length=1, max_length=200)
    external_assignment_id: str = Field(min_length=1, max_length=200)


class LmsAssignmentLinkRecord(LmsAssignmentLinkCreate):
    id: str
    provider: LmsProvider
    created_by: str
    created_at: datetime
    updated_at: datetime


class LmsAssignmentImportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignment: AcademicAssignmentRecord
    link: LmsAssignmentLinkRecord


class GradeSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str | None = Field(default=None, max_length=80)
    student_id_type: StudentIdType = StudentIdType.SIS_USER_ID
    dry_run: bool = False

    @field_validator("job_id")
    @classmethod
    def normalize_job_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class GradeSyncDelivery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str
    posted_grade: str
    status: str
    detail: str | None = None


class GradeSyncReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_assignment_id: str
    provider: LmsProvider
    dry_run: bool
    attempted: int = Field(ge=0)
    sent: int = Field(ge=0)
    skipped: int = Field(ge=0)
    failed: int = Field(ge=0)
    deliveries: list[GradeSyncDelivery]
