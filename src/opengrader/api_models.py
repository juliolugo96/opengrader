"""Configuration and durable models for the OpenGrader HTTP API."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from opengrader.dashboard_contract import cohort_totals, normalize_job_request_payload
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
    pdf_storage_root: Path = Path(".opengrader/pdfs")
    assignment_storage_root: Path = Path(".opengrader/assignments")
    pdf_max_upload_bytes: int = 10 * 1024 * 1024
    pdf_max_pages: int = 200
    billing_enabled: bool = False
    stripe_secret_key: str | None = field(default=None, repr=False)
    stripe_webhook_secret: str | None = field(default=None, repr=False)
    stripe_price_id: str | None = None
    public_url: str = "http://localhost:3000"
    stripe_meter_event_name: str = "opengrader_grading_units"
    canvas_base_url: str | None = None
    canvas_access_token: str | None = field(default=None, repr=False)
    canvas_account_name: str | None = None
    api_keys: tuple[str, ...] = ()
    poll_interval: float = 0.25

    def __post_init__(self) -> None:
        if self.poll_interval <= 0:
            raise ValueError("poll_interval must be positive")
        if self.pdf_max_upload_bytes <= 0:
            raise ValueError("pdf_max_upload_bytes must be positive")
        if self.pdf_max_pages <= 0:
            raise ValueError("pdf_max_pages must be positive")
        if self.billing_enabled and not all(
            (self.stripe_secret_key, self.stripe_webhook_secret, self.stripe_price_id)
        ):
            raise ValueError(
                "Hosted billing requires STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, "
                "and OPENGRADER_STRIPE_PRICE_ID"
            )
        if not self.public_url.startswith(("http://", "https://")):
            raise ValueError("public_url must use HTTP or HTTPS")
        if not 1 <= len(self.stripe_meter_event_name) <= 100:
            raise ValueError(
                "stripe_meter_event_name must contain between 1 and 100 characters"
            )
        if bool(self.canvas_base_url) != bool(self.canvas_access_token):
            raise ValueError(
                "Canvas integration requires OPENGRADER_CANVAS_BASE_URL and "
                "OPENGRADER_CANVAS_ACCESS_TOKEN together"
            )

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
            pdf_storage_root=Path(
                os.getenv("OPENGRADER_PDF_STORAGE_ROOT", ".opengrader/pdfs")
            ),
            assignment_storage_root=Path(
                os.getenv(
                    "OPENGRADER_ASSIGNMENT_STORAGE_ROOT", ".opengrader/assignments"
                )
            ),
            pdf_max_upload_bytes=int(
                os.getenv("OPENGRADER_PDF_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024))
            ),
            pdf_max_pages=int(os.getenv("OPENGRADER_PDF_MAX_PAGES", "200")),
            billing_enabled=_env_bool("OPENGRADER_BILLING_ENABLED", False),
            stripe_secret_key=os.getenv("STRIPE_SECRET_KEY") or None,
            stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET") or None,
            stripe_price_id=os.getenv("OPENGRADER_STRIPE_PRICE_ID") or None,
            public_url=os.getenv("OPENGRADER_PUBLIC_URL", "http://localhost:3000"),
            stripe_meter_event_name=os.getenv(
                "OPENGRADER_STRIPE_METER_EVENT_NAME", "opengrader_grading_units"
            ),
            canvas_base_url=os.getenv("OPENGRADER_CANVAS_BASE_URL") or None,
            canvas_access_token=os.getenv("OPENGRADER_CANVAS_ACCESS_TOKEN") or None,
            canvas_account_name=os.getenv("OPENGRADER_CANVAS_ACCOUNT_NAME") or None,
            api_keys=keys,
            poll_interval=float(os.getenv("OPENGRADER_POLL_INTERVAL", "0.25")),
        )


def api_key_id(api_key: str) -> str:
    """Return a non-secret stable identifier suitable for audit records."""

    # A 96-bit fingerprint remains compact in audit records while avoiding the
    # collision risk of a 48-bit identifier now that it also scopes billing.
    return hashlib.sha256(api_key.encode()).hexdigest()[:24]


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")
