"""Authenticated FastAPI application for durable grading jobs."""

import os
import secrets
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Security,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from opengrader import __version__
from opengrader.academic import (
    AcademicAssignmentCreate,
    AcademicAssignmentLaunch,
    AcademicAssignmentRecord,
    AssignmentKind,
)
from opengrader.academic_repository import AcademicAssignmentRepository
from opengrader.academic_service import AcademicAssignmentService
from opengrader.billing import (
    BillingCheckoutRequest,
    BillingOverview,
    BillingSessionResponse,
    BillingWebhookResponse,
)
from opengrader.billing_repository import BillingRepository
from opengrader.billing_service import (
    BillingGateway,
    BillingNotConfigured,
    BillingRequired,
    BillingService,
    BillingUsageWorker,
    BillingWebhookError,
)
from opengrader.canvas_adapter import CanvasAdapter
from opengrader.api_models import (
    ApiJobRequest,
    ApiSettings,
    AuditEvent,
    JobResponse,
    JobResultResponse,
    JobStatus,
    ResultStatistics,
    api_key_id,
)
from opengrader.lms import (
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
)
from opengrader.lms_adapter import (
    LmsAdapter,
    LmsAdapterRegistry,
    LmsNotConfigured,
    LmsRemoteError,
)
from opengrader.lms_repository import LmsRepository
from opengrader.lms_service import LmsService
from opengrader.repository import JobRepository
from opengrader.pdf_grading import PdfGradeRequest, PdfSubmissionRecord
from opengrader.pdf_repository import PdfSubmissionRepository
from opengrader.pdf_service import PdfGradingService, PdfUploadTooLarge
from opengrader.similarity import (
    SimilarityJobRequest,
    SimilarityJobResponse,
    SimilarityJobStatus,
    SimilarityReport,
)
from opengrader.similarity_repository import SimilarityRepository
from opengrader.similarity_service import SimilarityService, SimilarityTextExtractor
from opengrader.similarity_worker import SimilarityWorker
from opengrader.stripe_gateway import StripeBillingGateway
from opengrader.worker import JobWorker, RunnerFactory, default_runner_factory


def create_app(
    settings: ApiSettings | None = None,
    *,
    runner_factory: RunnerFactory = default_runner_factory,
    billing_gateway: BillingGateway | None = None,
    lms_adapters: Iterable[LmsAdapter] | None = None,
    similarity_text_extractor: SimilarityTextExtractor | None = None,
) -> FastAPI:
    """Build an independently configurable API application."""

    active_settings = settings or ApiSettings.from_env()
    repository = JobRepository(active_settings.database_path)
    academic_repository = AcademicAssignmentRepository(active_settings.database_path)
    academic_service = AcademicAssignmentService(
        academic_repository, storage_root=active_settings.assignment_storage_root
    )
    pdf_repository = PdfSubmissionRepository(active_settings.database_path)
    similarity_repository = SimilarityRepository(active_settings.database_path)
    lms_repository = LmsRepository(active_settings.database_path)
    active_lms_adapters = list(lms_adapters or ())
    if lms_adapters is None and active_settings.canvas_base_url:
        active_lms_adapters.append(
            CanvasAdapter(
                base_url=active_settings.canvas_base_url,
                access_token=active_settings.canvas_access_token or "",
                account_name=active_settings.canvas_account_name,
            )
        )
    lms_registry = LmsAdapterRegistry(active_lms_adapters)
    billing_repository = BillingRepository(active_settings.database_path)
    active_billing_gateway = billing_gateway
    if active_settings.billing_enabled and active_billing_gateway is None:
        active_billing_gateway = StripeBillingGateway(
            secret_key=active_settings.stripe_secret_key or "",
            price_id=active_settings.stripe_price_id or "",
            public_url=active_settings.public_url,
        )
    billing_service = BillingService(
        billing_repository,
        enabled=active_settings.billing_enabled,
        gateway=active_billing_gateway,
        webhook_secret=active_settings.stripe_webhook_secret,
        price_id=active_settings.stripe_price_id,
        meter_event_name=active_settings.stripe_meter_event_name,
    )
    billing_usage_worker = BillingUsageWorker(billing_service)
    pdf_service = PdfGradingService(
        pdf_repository,
        storage_root=active_settings.pdf_storage_root,
        max_upload_bytes=active_settings.pdf_max_upload_bytes,
        max_pages=active_settings.pdf_max_pages,
    )
    similarity_service = SimilarityService(
        similarity_repository,
        academic_repository,
        pdf_repository,
        storage_root=active_settings.pdf_storage_root,
        text_extractor=similarity_text_extractor,
    )
    lms_service = LmsService(
        registry=lms_registry,
        repository=lms_repository,
        academic_service=academic_service,
        academic_repository=academic_repository,
        job_repository=repository,
        pdf_repository=pdf_repository,
    )
    worker = JobWorker(
        repository,
        output_root=active_settings.output_root,
        poll_interval=active_settings.poll_interval,
        runner_factory=runner_factory,
    )
    similarity_worker = SimilarityWorker(
        similarity_repository,
        similarity_service,
        poll_interval=active_settings.poll_interval,
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        del application
        repository.initialize()
        academic_repository.initialize()
        pdf_repository.initialize()
        similarity_repository.initialize()
        lms_repository.initialize()
        billing_repository.initialize()
        worker.start()
        similarity_worker.start()
        billing_usage_worker.start()
        try:
            yield
        finally:
            worker.stop()
            similarity_worker.stop()
            billing_usage_worker.stop()

    application = FastAPI(
        title="OpenGrader API",
        version=__version__,
        lifespan=lifespan,
    )
    application.state.settings = active_settings
    application.state.repository = repository
    application.state.academic_repository = academic_repository
    application.state.academic_service = academic_service
    application.state.pdf_repository = pdf_repository
    application.state.pdf_service = pdf_service
    application.state.similarity_repository = similarity_repository
    application.state.similarity_service = similarity_service
    application.state.similarity_worker = similarity_worker
    application.state.lms_repository = lms_repository
    application.state.lms_registry = lms_registry
    application.state.lms_service = lms_service
    application.state.billing_repository = billing_repository
    application.state.billing_service = billing_service
    application.state.billing_usage_worker = billing_usage_worker
    application.state.worker = worker

    bearer = HTTPBearer(auto_error=False)

    def authenticate(
        credentials: Annotated[
            HTTPAuthorizationCredentials | None, Security(bearer)
        ] = None,
    ) -> str:
        if not active_settings.api_keys:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="API authentication is not configured",
            )
        if credentials is None:
            raise _unauthorized()

        supplied = credentials.credentials
        matched = False
        for configured in active_settings.api_keys:
            matched = secrets.compare_digest(supplied, configured) or matched
        if not matched:
            raise _unauthorized()
        return f"key:{api_key_id(supplied)}"

    Actor = Annotated[str, Depends(authenticate)]

    @application.get("/health", tags=["system"])
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "version": __version__,
            "authentication_configured": bool(active_settings.api_keys),
        }

    @application.get(
        "/v1/lms/providers",
        response_model=list[LmsConnectionStatus],
        tags=["lms integrations"],
    )
    def list_lms_providers(actor: Actor) -> list[LmsConnectionStatus]:
        del actor
        return lms_service.statuses()

    @application.get(
        "/v1/lms/{provider}/courses",
        response_model=list[LmsCourse],
        tags=["lms integrations"],
    )
    def list_lms_courses(provider: LmsProvider, actor: Actor) -> list[LmsCourse]:
        del actor
        try:
            return lms_service.courses(provider)
        except LmsNotConfigured as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except LmsRemoteError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @application.get(
        "/v1/lms/{provider}/courses/{course_id}/assignments",
        response_model=list[LmsAssignment],
        tags=["lms integrations"],
    )
    def list_lms_assignments(
        provider: LmsProvider, course_id: str, actor: Actor
    ) -> list[LmsAssignment]:
        del actor
        try:
            return lms_service.assignments(provider, course_id)
        except LmsNotConfigured as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (LmsRemoteError, ValueError) as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @application.post(
        "/v1/lms/{provider}/imports",
        response_model=LmsAssignmentImportResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["lms integrations", "assignments"],
    )
    def import_lms_assignment(
        provider: LmsProvider, request: LmsAssignmentImport, actor: Actor
    ) -> LmsAssignmentImportResponse:
        try:
            return lms_service.import_assignment(provider, request, actor=actor)
        except LmsNotConfigured as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except LmsRemoteError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.get(
        "/v1/lms/links",
        response_model=list[LmsAssignmentLinkRecord],
        tags=["lms integrations"],
    )
    def list_lms_links(actor: Actor) -> list[LmsAssignmentLinkRecord]:
        del actor
        return lms_repository.list_links()

    @application.post(
        "/v1/lms/{provider}/links",
        response_model=LmsAssignmentLinkRecord,
        status_code=status.HTTP_201_CREATED,
        tags=["lms integrations", "assignments"],
    )
    def link_lms_assignment(
        provider: LmsProvider, request: LmsAssignmentLinkCreate, actor: Actor
    ) -> LmsAssignmentLinkRecord:
        try:
            return lms_service.link_assignment(provider, request, actor=actor)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Assignment not found") from exc
        except LmsNotConfigured as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except LmsRemoteError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.delete(
        "/v1/lms/links/{local_assignment_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["lms integrations"],
    )
    def unlink_lms_assignment(local_assignment_id: str, actor: Actor) -> None:
        if not lms_repository.delete_link(local_assignment_id, actor=actor):
            raise HTTPException(status_code=404, detail="LMS link not found")

    @application.post(
        "/v1/lms/links/{local_assignment_id}/grades",
        response_model=GradeSyncReport,
        tags=["lms integrations"],
    )
    def sync_lms_grades(
        local_assignment_id: str, request: GradeSyncRequest, actor: Actor
    ) -> GradeSyncReport:
        try:
            return lms_service.sync_grades(local_assignment_id, request, actor=actor)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Assignment, link, or job not found") from exc
        except (LmsNotConfigured, ValueError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.post(
        "/v1/jobs",
        response_model=JobResponse,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["jobs"],
    )
    def create_job(request: ApiJobRequest, actor: Actor) -> JobResponse:
        _require_billing_entitlement(billing_service, actor)
        job = repository.create_job(request, actor=actor)
        billing_service.record_usage(actor, resource_type="job", resource_id=job.id)
        billing_usage_worker.notify()
        worker.notify()
        return JobResponse.from_record(job)

    @application.post(
        "/v1/assignments",
        response_model=AcademicAssignmentRecord,
        status_code=status.HTTP_201_CREATED,
        tags=["assignments"],
    )
    def create_academic_assignment(
        request: AcademicAssignmentCreate, actor: Actor
    ) -> AcademicAssignmentRecord:
        return academic_service.create(request, actor=actor)

    @application.get(
        "/v1/assignments",
        response_model=list[AcademicAssignmentRecord],
        tags=["assignments"],
    )
    def list_academic_assignments(
        actor: Actor,
        institution: Annotated[str | None, Query(max_length=160)] = None,
        course_code: Annotated[str | None, Query(max_length=40)] = None,
        period: Annotated[str | None, Query(max_length=80)] = None,
        section: Annotated[str | None, Query(max_length=80)] = None,
        kind: AssignmentKind | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> list[AcademicAssignmentRecord]:
        del actor
        return academic_repository.list(
            institution=institution,
            course_code=course_code,
            period=period,
            section=section,
            kind=kind,
            limit=limit,
            offset=offset,
        )

    @application.get(
        "/v1/assignments/{assignment_id}",
        response_model=AcademicAssignmentRecord,
        tags=["assignments"],
    )
    def get_academic_assignment(
        assignment_id: str, actor: Actor
    ) -> AcademicAssignmentRecord:
        del actor
        record = academic_repository.get(assignment_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Assignment not found")
        return record

    @application.put(
        "/v1/assignments/{assignment_id}",
        response_model=AcademicAssignmentRecord,
        tags=["assignments"],
    )
    def update_academic_assignment(
        assignment_id: str, request: AcademicAssignmentCreate, actor: Actor
    ) -> AcademicAssignmentRecord:
        try:
            return academic_service.update(assignment_id, request, actor=actor)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Assignment not found") from exc

    @application.delete(
        "/v1/assignments/{assignment_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["assignments"],
    )
    def delete_academic_assignment(assignment_id: str, actor: Actor) -> None:
        if not academic_service.delete(assignment_id, actor=actor):
            raise HTTPException(status_code=404, detail="Assignment not found")

    @application.post(
        "/v1/assignments/{assignment_id}/jobs",
        response_model=JobResponse,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["assignments", "jobs"],
    )
    def launch_academic_assignment(
        assignment_id: str, request: AcademicAssignmentLaunch, actor: Actor
    ) -> JobResponse:
        _require_billing_entitlement(billing_service, actor)
        try:
            job_request = academic_service.job_request(assignment_id, request)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Assignment not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        job = repository.create_job(job_request, actor=actor)
        billing_service.record_usage(actor, resource_type="job", resource_id=job.id)
        billing_usage_worker.notify()
        worker.notify()
        return JobResponse.from_record(job)

    @application.get("/v1/jobs", response_model=list[JobResponse], tags=["jobs"])
    def list_jobs(
        actor: Actor,
        job_status: Annotated[JobStatus | None, Query(alias="status")] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> list[JobResponse]:
        del actor
        return [
            JobResponse.from_record(job)
            for job in repository.list_jobs(
                status=job_status, limit=limit, offset=offset
            )
        ]

    @application.get(
        "/v1/jobs/{job_id}", response_model=JobResponse, tags=["jobs"]
    )
    def get_job(job_id: str, actor: Actor) -> JobResponse:
        del actor
        job = repository.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return JobResponse.from_record(job)

    @application.get(
        "/v1/jobs/{job_id}/result",
        response_model=JobResultResponse,
        tags=["jobs"],
    )
    def get_job_result(job_id: str, actor: Actor) -> JobResultResponse:
        del actor
        job = repository.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status is not JobStatus.SUCCEEDED or job.result is None:
            raise HTTPException(status_code=409, detail="Job result is not available")
        return JobResultResponse(
            job_id=job.id,
            result=job.result,
            reports=job.reports,
            statistics=ResultStatistics.from_result(job.result),
        )

    @application.post(
        "/v1/pdf-submissions",
        response_model=PdfSubmissionRecord,
        status_code=status.HTTP_201_CREATED,
        tags=["pdf grading"],
    )
    async def create_pdf_submission(
        actor: Actor,
        student_id: Annotated[str, Form(min_length=1, max_length=120)],
        title: Annotated[str, Form(min_length=1, max_length=200)],
        file: Annotated[UploadFile, File()],
        assignment_id: Annotated[str | None, Form(max_length=80)] = None,
    ) -> PdfSubmissionRecord:
        _require_billing_entitlement(billing_service, actor)
        if assignment_id is not None:
            assignment = academic_repository.get(assignment_id)
            if assignment is None:
                raise HTTPException(status_code=404, detail="Assignment not found")
            if assignment.kind is not AssignmentKind.PDF:
                raise HTTPException(
                    status_code=409,
                    detail="PDF submissions require a PDF assignment",
                )
        try:
            submission = await pdf_service.ingest(
                file,
                student_id=student_id,
                title=title,
                actor=actor,
                assignment_id=assignment_id,
            )
            billing_service.record_usage(
                actor,
                resource_type="pdf_submission",
                resource_id=submission.id,
            )
            billing_usage_worker.notify()
            return submission
        except PdfUploadTooLarge as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @application.get(
        "/v1/billing/overview",
        response_model=BillingOverview,
        tags=["billing"],
    )
    def get_billing_overview(actor: Actor) -> BillingOverview:
        return billing_service.overview(actor)

    @application.post(
        "/v1/billing/checkout",
        response_model=BillingSessionResponse,
        tags=["billing"],
    )
    def create_billing_checkout(
        request: BillingCheckoutRequest, actor: Actor
    ) -> BillingSessionResponse:
        try:
            return billing_service.create_checkout(actor, email=request.email)
        except (BillingNotConfigured, BillingRequired) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.post(
        "/v1/billing/portal",
        response_model=BillingSessionResponse,
        tags=["billing"],
    )
    def create_billing_portal(actor: Actor) -> BillingSessionResponse:
        try:
            return billing_service.create_portal(actor)
        except (BillingNotConfigured, BillingRequired) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.post(
        "/v1/billing/webhook",
        response_model=BillingWebhookResponse,
        tags=["billing"],
    )
    async def receive_billing_webhook(request: Request) -> BillingWebhookResponse:
        signature = request.headers.get("stripe-signature")
        if not signature:
            raise HTTPException(status_code=400, detail="Stripe signature is missing")
        try:
            processed = billing_service.handle_webhook(await request.body(), signature)
        except (BillingNotConfigured, BillingWebhookError) as exc:
            raise HTTPException(status_code=400, detail="Invalid Stripe webhook") from exc
        billing_usage_worker.notify()
        return BillingWebhookResponse(processed=processed)

    @application.get(
        "/v1/pdf-submissions",
        response_model=list[PdfSubmissionRecord],
        tags=["pdf grading"],
    )
    def list_pdf_submissions(
        actor: Actor,
        assignment_id: str | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> list[PdfSubmissionRecord]:
        del actor
        return pdf_repository.list_submissions(
            assignment_id=assignment_id, limit=limit, offset=offset
        )

    @application.get(
        "/v1/pdf-submissions/{submission_id}",
        response_model=PdfSubmissionRecord,
        tags=["pdf grading"],
    )
    def get_pdf_submission(submission_id: str, actor: Actor) -> PdfSubmissionRecord:
        del actor
        record = pdf_repository.get_submission(submission_id)
        if record is None:
            raise HTTPException(status_code=404, detail="PDF submission not found")
        return record

    @application.get(
        "/v1/pdf-submissions/{submission_id}/document",
        response_class=FileResponse,
        tags=["pdf grading"],
    )
    def get_pdf_document(submission_id: str, actor: Actor) -> FileResponse:
        del actor
        record = pdf_repository.get_submission(submission_id)
        if record is None:
            raise HTTPException(status_code=404, detail="PDF submission not found")
        return FileResponse(
            pdf_service.original_path(submission_id),
            media_type="application/pdf",
            filename=record.original_filename,
            content_disposition_type="inline",
        )

    @application.put(
        "/v1/pdf-submissions/{submission_id}/grade",
        response_model=PdfSubmissionRecord,
        tags=["pdf grading"],
    )
    def save_pdf_grade(
        submission_id: str, grade: PdfGradeRequest, actor: Actor
    ) -> PdfSubmissionRecord:
        try:
            return pdf_service.save_grade(submission_id, grade=grade, actor=actor)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="PDF submission not found") from exc
        except ValueError as exc:
            status_code = 409 if "Finalized" in str(exc) else 422
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    @application.get(
        "/v1/pdf-submissions/{submission_id}/feedback.pdf",
        response_class=FileResponse,
        tags=["pdf grading"],
    )
    def get_pdf_feedback(submission_id: str, actor: Actor) -> FileResponse:
        del actor
        record = pdf_repository.get_submission(submission_id)
        if record is None:
            raise HTTPException(status_code=404, detail="PDF submission not found")
        try:
            path = pdf_service.feedback_path(record)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return FileResponse(
            path,
            media_type="application/pdf",
            filename=f"{record.id}-feedback.pdf",
        )

    @application.post(
        "/v1/similarity/jobs",
        response_model=SimilarityJobResponse,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["similarity review"],
    )
    def create_similarity_job(
        request: SimilarityJobRequest, actor: Actor
    ) -> SimilarityJobResponse:
        _require_billing_entitlement(billing_service, actor)
        try:
            job = similarity_service.create(request, actor=actor)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Assignment not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        similarity_worker.notify()
        return SimilarityJobResponse.from_record(job)

    @application.get(
        "/v1/similarity/jobs",
        response_model=list[SimilarityJobResponse],
        tags=["similarity review"],
    )
    def list_similarity_jobs(
        actor: Actor,
        assignment_id: Annotated[str | None, Query(max_length=80)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> list[SimilarityJobResponse]:
        del actor
        return [
            SimilarityJobResponse.from_record(job)
            for job in similarity_repository.list(
                assignment_id=assignment_id, limit=limit, offset=offset
            )
        ]

    @application.get(
        "/v1/similarity/jobs/{job_id}",
        response_model=SimilarityJobResponse,
        tags=["similarity review"],
    )
    def get_similarity_job(job_id: str, actor: Actor) -> SimilarityJobResponse:
        del actor
        job = similarity_repository.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Similarity job not found")
        return SimilarityJobResponse.from_record(job)

    @application.get(
        "/v1/similarity/jobs/{job_id}/report",
        response_model=SimilarityReport,
        tags=["similarity review"],
    )
    def get_similarity_report(job_id: str, actor: Actor) -> SimilarityReport:
        del actor
        job = similarity_repository.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Similarity job not found")
        if job.status is not SimilarityJobStatus.SUCCEEDED or job.report is None:
            raise HTTPException(status_code=409, detail="Similarity report is not available")
        return job.report

    @application.get(
        "/v1/audit-events",
        response_model=list[AuditEvent],
        tags=["audit"],
    )
    def list_audit_events(
        actor: Actor,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
    ) -> list[AuditEvent]:
        del actor
        return repository.list_audit_events(limit=limit)

    return application


def _require_billing_entitlement(service: BillingService, actor: str) -> None:
    try:
        service.require_entitlement(actor)
    except BillingRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)
        ) from exc


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
        headers={"WWW-Authenticate": "Bearer"},
    )


app = create_app()


def main() -> None:
    """Run the API with Uvicorn using environment-based configuration."""

    uvicorn.run(
        "opengrader.api:app",
        host=os.getenv("OPENGRADER_HOST", "127.0.0.1"),
        port=int(os.getenv("OPENGRADER_PORT", "8000")),
    )
