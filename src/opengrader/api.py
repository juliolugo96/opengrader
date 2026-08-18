"""Authenticated FastAPI application for durable grading jobs."""

import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Security, status
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
from opengrader.worker import JobWorker, RunnerFactory, default_runner_factory


def create_app(
    settings: ApiSettings | None = None,
    *,
    runner_factory: RunnerFactory = default_runner_factory,
) -> FastAPI:
    """Build an independently configurable API application."""

    active_settings = settings or ApiSettings.from_env()
    repository = JobRepository(active_settings.database_path)
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
