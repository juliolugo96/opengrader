"""Domain contracts for assignment-scoped structural similarity review."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

STRUCTURAL_ALGORITHM_VERSION = "structural-winnowing-v1"


class SimilarityJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class SimilarityBand(StrEnum):
    REVIEW = "review"
    HIGH_SIGNAL = "high_signal"


class SimilarityPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ngram_size: int = Field(default=5, ge=2, le=20)
    window_size: int = Field(default=4, ge=2, le=30)
    min_shared_fingerprints: int = Field(default=2, ge=1, le=100)
    review_threshold: float = Field(default=0.25, ge=0, le=1)
    high_signal_threshold: float = Field(default=0.65, ge=0, le=1)
    max_documents: int = Field(default=200, ge=2, le=1_000)
    max_candidate_pairs: int = Field(default=10_000, ge=1, le=100_000)
    max_evidence_per_match: int = Field(default=5, ge=1, le=20)
    max_characters_per_document: int = Field(
        default=1_000_000, ge=1_000, le=10_000_000
    )

    @model_validator(mode="after")
    def ordered_thresholds(self) -> Self:
        if self.high_signal_threshold <= self.review_threshold:
            raise ValueError("high_signal_threshold must exceed review_threshold")
        return self


class SimilarityJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignment_id: str = Field(min_length=1, max_length=80)
    policy: SimilarityPolicy = Field(default_factory=SimilarityPolicy)


class SimilarityDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submission_id: str
    student_id: str
    text: str


class SimilarityEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fingerprint: str
    left_excerpt: str
    right_excerpt: str
    left_start: int = Field(ge=0)
    left_end: int = Field(ge=0)
    right_start: int = Field(ge=0)
    right_end: int = Field(ge=0)


class SimilarityMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left_submission_id: str
    left_student_id: str
    right_submission_id: str
    right_student_id: str
    score: float = Field(ge=0, le=1)
    containment: float = Field(ge=0, le=1)
    jaccard: float = Field(ge=0, le=1)
    coverage: float = Field(ge=0, le=1)
    band: SimilarityBand
    exact_match: bool = False
    shared_fingerprints: int = Field(ge=0)
    evidence: list[SimilarityEvidence] = Field(default_factory=list)


class SimilarityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    assignment_id: str
    algorithm_version: str = STRUCTURAL_ALGORITHM_VERSION
    generated_at: datetime
    corpus_size: int = Field(ge=0)
    candidate_pairs_evaluated: int = Field(ge=0)
    matches: list[SimilarityMatch] = Field(default_factory=list)
    indeterminate_documents: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "Similarity signals support instructor review; they do not determine plagiarism "
        "or academic misconduct."
    )


class SimilarityJobRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    assignment_id: str
    status: SimilarityJobStatus
    request: SimilarityJobRequest
    submission_ids: list[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    report: SimilarityReport | None = None
    error: str | None = None


class SimilarityJobResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    assignment_id: str
    status: SimilarityJobStatus
    request: SimilarityJobRequest
    submission_count: int = Field(ge=0)
    created_by: str
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None

    @classmethod
    def from_record(cls, job: SimilarityJobRecord) -> SimilarityJobResponse:
        return cls(
            id=job.id,
            assignment_id=job.assignment_id,
            status=job.status,
            request=job.request,
            submission_count=len(job.submission_ids),
            created_by=job.created_by,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error=job.error,
        )
