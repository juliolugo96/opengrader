"""Professor-facing academic organization and assignment contracts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from opengrader.config import TestConfig


class AssignmentKind(StrEnum):
    AUTOMATED = "automated"
    PDF = "pdf"


class AcademicContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution: str = Field(min_length=1, max_length=160)
    course_code: str = Field(min_length=1, max_length=40)
    course_name: str = Field(min_length=1, max_length=160)
    period: str = Field(min_length=1, max_length=80)
    section: str = Field(min_length=1, max_length=80)

    @field_validator("institution", "course_code", "course_name", "period", "section")
    @classmethod
    def strip_nonblank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized


class AutomatedAssignmentDefinition(BaseModel):
    """Structured engine settings created by the visual assignment builder."""

    model_config = ConfigDict(extra="forbid")

    image: str = Field(default="python:3.12-slim", min_length=1, max_length=300)
    setup: str | None = None
    timeout_seconds: Annotated[float, Field(gt=0, le=3600)] = 10
    memory_mb: Annotated[int, Field(ge=32, le=32768)] = 256
    cpus: Annotated[float, Field(gt=0, le=32)] = 1
    pids_limit: Annotated[int, Field(ge=16, le=4096)] = 128
    tests: list[TestConfig] = Field(min_length=1, max_length=100)

    @field_validator("image")
    @classmethod
    def strip_image(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized

    @field_validator("setup")
    @classmethod
    def strip_setup(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def test_names_are_unique(self) -> Self:
        names = [test.name for test in self.tests]
        if len(names) != len(set(names)):
            raise ValueError("test names must be unique")
        return self


class AcademicAssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    kind: AssignmentKind
    context: AcademicContext
    automated: AutomatedAssignmentDefinition | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized

    @model_validator(mode="after")
    def matching_definition(self) -> Self:
        if self.kind is AssignmentKind.AUTOMATED and self.automated is None:
            raise ValueError("automated assignments require evaluation checks")
        if self.kind is AssignmentKind.PDF and self.automated is not None:
            raise ValueError("PDF assignments cannot include automated checks")
        return self


class AcademicAssignmentRecord(AcademicAssignmentCreate):
    id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class AcademicAssignmentLaunch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submissions_dir: str = Field(min_length=1, max_length=2_000)
    no_docker: bool = False
    workers: int = Field(default=1, ge=1, le=64)
    retries: int = Field(default=0, ge=0, le=10)
    submission_patterns: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("submissions_dir")
    @classmethod
    def strip_submissions_dir(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized
