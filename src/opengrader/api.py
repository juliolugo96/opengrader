"""Authenticated FastAPI application for durable grading jobs."""

import os
import secrets
from collections.abc import AsyncIterator
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
    Security,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from opengrader import __version__
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
from opengrader.repository import JobRepository
from opengrader.pdf_grading import PdfGradeRequest, PdfSubmissionRecord
from opengrader.pdf_repository import PdfSubmissionRepository
from opengrader.pdf_service import PdfGradingService, PdfUploadTooLarge
from opengrader.worker import JobWorker, RunnerFactory, default_runner_factory


def create_app(
    settings: ApiSettings | None = None,
    *,
    runner_factory: RunnerFactory = default_runner_factory,
) -> FastAPI:
    """Build an independently configurable API application."""

    active_settings = settings or ApiSettings.from_env()
    repository = JobRepository(active_settings.database_path)
    pdf_repository = PdfSubmissionRepository(active_settings.database_path)
    pdf_service = PdfGradingService(
        pdf_repository,
        storage_root=active_settings.pdf_storage_root,
        max_upload_bytes=active_settings.pdf_max_upload_bytes,
        max_pages=active_settings.pdf_max_pages,
    )
    worker = JobWorker(
        repository,
        output_root=active_settings.output_root,
        poll_interval=active_settings.poll_interval,
        runner_factory=runner_factory,
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        del application
        repository.initialize()
        pdf_repository.initialize()
        worker.start()
        try:
            yield
        finally:
            worker.stop()

    application = FastAPI(
        title="OpenGrader API",
        version=__version__,
        lifespan=lifespan,
    )
    application.state.settings = active_settings
    application.state.repository = repository
    application.state.pdf_repository = pdf_repository
    application.state.pdf_service = pdf_service
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

    @application.post(
        "/v1/jobs",
        response_model=JobResponse,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["jobs"],
    )
    def create_job(request: ApiJobRequest, actor: Actor) -> JobResponse:
        job = repository.create_job(request, actor=actor)
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
    ) -> PdfSubmissionRecord:
        try:
            return await pdf_service.ingest(
                file, student_id=student_id, title=title, actor=actor
            )
        except PdfUploadTooLarge as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @application.get(
        "/v1/pdf-submissions",
        response_model=list[PdfSubmissionRecord],
        tags=["pdf grading"],
    )
    def list_pdf_submissions(
        actor: Actor,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> list[PdfSubmissionRecord]:
        del actor
        return pdf_repository.list_submissions(limit=limit, offset=offset)

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
