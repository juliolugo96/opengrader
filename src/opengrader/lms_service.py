"""Application orchestration for LMS discovery, import, linking, and grade sync."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from opengrader.academic import AcademicAssignmentCreate, AssignmentKind
from opengrader.academic_repository import AcademicAssignmentRepository
from opengrader.academic_service import AcademicAssignmentService
from opengrader.api_models import JobStatus
from opengrader.lms import (
    GradeSyncDelivery,
    GradeSyncReport,
    GradeSyncRequest,
    LmsAssignment,
    LmsAssignmentImport,
    LmsAssignmentImportResponse,
    LmsAssignmentLinkCreate,
    LmsAssignmentLinkRecord,
    LmsConnectionStatus,
    LmsCourse,
    LmsProvider,
    grade_percentage,
)
from opengrader.lms_adapter import LmsAdapterRegistry
from opengrader.lms_repository import LmsRepository
from opengrader.pdf_grading import PdfSubmissionStatus
from opengrader.pdf_repository import PdfSubmissionRepository
from opengrader.repository import JobRepository


@dataclass(frozen=True, slots=True)
class _GradeCandidate:
    student_id: str
    score: float
    maximum: float
    source_revision: str


class LmsService:
    def __init__(
        self,
        *,
        registry: LmsAdapterRegistry,
        repository: LmsRepository,
        academic_service: AcademicAssignmentService,
        academic_repository: AcademicAssignmentRepository,
        job_repository: JobRepository,
        pdf_repository: PdfSubmissionRepository,
    ) -> None:
        self.registry = registry
        self.repository = repository
        self.academic_service = academic_service
        self.academic_repository = academic_repository
        self.job_repository = job_repository
        self.pdf_repository = pdf_repository

    def statuses(self) -> list[LmsConnectionStatus]:
        return self.registry.statuses()

    def courses(self, provider: LmsProvider) -> list[LmsCourse]:
        return self.registry.get(provider).list_courses()

    def assignments(self, provider: LmsProvider, course_id: str) -> list[LmsAssignment]:
        return self.registry.get(provider).list_assignments(course_id)

    def import_assignment(
        self, provider: LmsProvider, request: LmsAssignmentImport, *, actor: str
    ) -> LmsAssignmentImportResponse:
        remote = self.registry.get(provider).get_assignment(
            request.external_course_id, request.external_assignment_id
        )
        assignment = self.academic_service.create(
            AcademicAssignmentCreate(
                name=remote.name,
                kind=request.kind,
                context=request.context,
                automated=request.automated,
            ),
            actor=actor,
        )
        try:
            link = self.repository.create_link(
                local_assignment_id=assignment.id,
                provider=provider,
                external_course_id=request.external_course_id,
                external_assignment_id=request.external_assignment_id,
                actor=actor,
            )
        except Exception:
            self.academic_service.delete(assignment.id, actor=actor)
            raise
        return LmsAssignmentImportResponse(assignment=assignment, link=link)

    def link_assignment(
        self, provider: LmsProvider, request: LmsAssignmentLinkCreate, *, actor: str
    ) -> LmsAssignmentLinkRecord:
        if self.academic_repository.get(request.local_assignment_id) is None:
            raise KeyError(request.local_assignment_id)
        self.registry.get(provider).get_assignment(
            request.external_course_id, request.external_assignment_id
        )
        return self.repository.create_link(
            local_assignment_id=request.local_assignment_id,
            provider=provider,
            external_course_id=request.external_course_id,
            external_assignment_id=request.external_assignment_id,
            actor=actor,
        )

    def sync_grades(
        self, local_assignment_id: str, request: GradeSyncRequest, *, actor: str
    ) -> GradeSyncReport:
        link = self.repository.get_link(local_assignment_id)
        if link is None:
            raise KeyError(local_assignment_id)
        assignment = self.academic_repository.get(local_assignment_id)
        if assignment is None:
            raise KeyError(local_assignment_id)
        adapter = self.registry.get(link.provider)
        candidates = self._candidates(assignment.kind, local_assignment_id, request)
        deliveries: list[GradeSyncDelivery] = []
        sent = skipped = failed = 0
        for candidate in candidates:
            posted_grade = grade_percentage(candidate.score, candidate.maximum)
            delivery_key = _delivery_key(
                link_id=link.id,
                student_id=candidate.student_id,
                student_id_type=request.student_id_type.value,
                posted_grade=posted_grade,
                source_revision=candidate.source_revision,
            )
            if self.repository.was_delivered(delivery_key):
                skipped += 1
                deliveries.append(GradeSyncDelivery(
                    student_id=candidate.student_id, posted_grade=posted_grade,
                    status="skipped", detail="Already delivered",
                ))
                continue
            if request.dry_run:
                deliveries.append(GradeSyncDelivery(
                    student_id=candidate.student_id, posted_grade=posted_grade,
                    status="planned",
                ))
                continue
            try:
                adapter.post_grade(
                    course_id=link.external_course_id,
                    assignment_id=link.external_assignment_id,
                    student_id=candidate.student_id,
                    student_id_type=request.student_id_type,
                    posted_grade=posted_grade,
                    comment="Grade synchronized from OpenGrader",
                )
            except Exception as exc:
                failed += 1
                deliveries.append(GradeSyncDelivery(
                    student_id=candidate.student_id, posted_grade=posted_grade,
                    status="failed", detail=str(exc)[:500],
                ))
                continue
            self.repository.record_delivery(
                delivery_key=delivery_key,
                link_id=link.id,
                student_id=candidate.student_id,
                posted_grade=posted_grade,
                source_revision=candidate.source_revision,
                actor=actor,
            )
            sent += 1
            deliveries.append(GradeSyncDelivery(
                student_id=candidate.student_id, posted_grade=posted_grade,
                status="sent",
            ))
        return GradeSyncReport(
            local_assignment_id=local_assignment_id,
            provider=link.provider,
            dry_run=request.dry_run,
            attempted=len(candidates),
            sent=sent,
            skipped=skipped,
            failed=failed,
            deliveries=deliveries,
        )

    def _candidates(
        self, kind: AssignmentKind, local_assignment_id: str, request: GradeSyncRequest
    ) -> list[_GradeCandidate]:
        if kind is AssignmentKind.AUTOMATED:
            if request.job_id is None:
                raise ValueError("Automated grade sync requires a completed job")
            job = self.job_repository.get_job(request.job_id)
            if job is None:
                raise KeyError(request.job_id)
            if job.status is not JobStatus.SUCCEEDED or job.result is None:
                raise ValueError("Automated grade sync requires a successful job")
            if job.request.assignment_file.stem != local_assignment_id:
                raise ValueError("The job does not belong to the linked assignment")
            return [
                _GradeCandidate(
                    student_id=result.student_id,
                    score=result.score,
                    maximum=result.maximum_score,
                    source_revision=f"job:{job.id}",
                )
                for result in job.result.submissions
            ]
        if request.job_id is not None:
            raise ValueError("PDF grade sync does not accept a job ID")
        records = []
        offset = 0
        while True:
            page = self.pdf_repository.list_submissions(
                assignment_id=local_assignment_id, limit=100, offset=offset
            )
            records.extend(page)
            if len(page) < 100:
                break
            offset += len(page)
        return [
            _GradeCandidate(
                student_id=record.student_id,
                score=record.total_score,
                maximum=record.maximum_points,
                source_revision=f"pdf:{record.id}:{record.updated_at.isoformat()}",
            )
            for record in records
            if record.status is PdfSubmissionStatus.FINALIZED and record.grade is not None
        ]


def _delivery_key(**values: str) -> str:
    payload = json.dumps(values, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
