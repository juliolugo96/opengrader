"""Configuration and durable models for the OpenGrader HTTP API."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from opengrader.mvp4_contract import cohort_totals, normalize_job_request_payload
from opengrader.results import GradingResult


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ApiJobRequest(BaseModel):
    """A serializable request for the existing grading pipeline."""

    model_config = ConfigDict(extra="forbid")

    assignment_file: Path
    submissions_dir: Path
    no_docker: bool = False
    workers: int = Field(default=1, ge=1, le=64)
    retries: int = Field(default=0, ge=0, le=10)
    submission_patterns: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def accept_documented_dashboard_fields(cls, value: Any) -> Any:
        return normalize_job_request_payload(value)


class JobRecord(BaseModel):
    """Complete persisted state for one grading job."""

    model_config = ConfigDict(extra="forbid")

    id: str
    status: JobStatus
    request: ApiJobRequest
    created_by: str
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: GradingResult | None = None
    reports: dict[str, str] = Field(default_factory=dict)
    error: str | None = None


class AuditEvent(BaseModel):
    """One append-only API or worker action."""

    model_config = ConfigDict(extra="forbid")

    id: int
    occurred_at: datetime
    actor: str
    action: str
    resource_type: str
    resource_id: str
    details: dict[str, object] = Field(default_factory=dict)


class JobResponse(BaseModel):
    """HTTP representation of job state without the potentially large result."""

    model_config = ConfigDict(extra="forbid")

    id: str
    status: JobStatus
    request: ApiJobRequest
    created_by: str
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    reports: dict[str, str] = Field(default_factory=dict)
    error: str | None = None

    @classmethod
    def from_record(cls, job: JobRecord) -> JobResponse:
        return cls.model_validate(
            job.model_dump(exclude={"result"}, exclude_computed_fields=True)
        )


class ResultStatistics(BaseModel):
    """Cohort-level totals returned with every completed result."""

    model_config = ConfigDict(extra="forbid")

    total_score: float = Field(ge=0)
    maximum_points: float = Field(ge=0)
    student_count: int = Field(ge=0)

    @classmethod
    def from_result(cls, result: GradingResult) -> ResultStatistics:
        total_score, maximum_points, student_count = cohort_totals(result)
        return cls(
            total_score=total_score,
            maximum_points=maximum_points,
            student_count=student_count,
        )


class JobResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    result: GradingResult
    reports: dict[str, str]
    statistics: ResultStatistics


@dataclass(frozen=True, slots=True)
class ApiSettings:
    database_path: Path = Path(".opengrader/jobs.db")
    output_root: Path = Path(".opengrader/reports")
    api_keys: tuple[str, ...] = ()
    poll_interval: float = 0.25

    def __post_init__(self) -> None:
        if self.poll_interval <= 0:
            raise ValueError("poll_interval must be positive")

    @classmethod
    def from_env(cls) -> ApiSettings:
        keys = tuple(
            dict.fromkeys(
                key.strip()
                for key in os.getenv("OPENGRADER_API_KEYS", "").split(",")
                if key.strip()
            )
        )
        return cls(
            database_path=Path(
                os.getenv("OPENGRADER_DATABASE", ".opengrader/jobs.db")
            ),
            output_root=Path(
                os.getenv("OPENGRADER_OUTPUT_ROOT", ".opengrader/reports")
            ),
            api_keys=keys,
            poll_interval=float(os.getenv("OPENGRADER_POLL_INTERVAL", "0.25")),
        )


def api_key_id(api_key: str) -> str:
    """Return a non-secret stable identifier suitable for audit records."""

    return hashlib.sha256(api_key.encode()).hexdigest()[:12]
