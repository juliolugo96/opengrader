"""Application service for visual assignment definitions and job launch."""

from __future__ import annotations

import uuid
from pathlib import Path

import yaml

from opengrader.academic import (
    AcademicAssignmentCreate,
    AcademicAssignmentLaunch,
    AcademicAssignmentRecord,
    AssignmentKind,
)
from opengrader.academic_repository import AcademicAssignmentRepository
from opengrader.api_models import ApiJobRequest
from opengrader.config import AssignmentConfig


class AcademicAssignmentService:
    def __init__(
        self, repository: AcademicAssignmentRepository, *, storage_root: Path
    ) -> None:
        self.repository = repository
        self.storage_root = storage_root

    def create(
        self, request: AcademicAssignmentCreate, *, actor: str
    ) -> AcademicAssignmentRecord:
        return self.repository.create(request, actor=actor)

    def update(
        self,
        assignment_id: str,
        request: AcademicAssignmentCreate,
        *,
        actor: str,
    ) -> AcademicAssignmentRecord:
        return self.repository.update(assignment_id, request, actor=actor)

    def delete(self, assignment_id: str, *, actor: str) -> bool:
        deleted = self.repository.delete(assignment_id, actor=actor)
        if deleted:
            self._path(assignment_id).unlink(missing_ok=True)
        return deleted

    def job_request(
        self, assignment_id: str, launch: AcademicAssignmentLaunch
    ) -> ApiJobRequest:
        record = self.repository.get(assignment_id)
        if record is None:
            raise KeyError(assignment_id)
        if record.kind is not AssignmentKind.AUTOMATED or record.automated is None:
            raise ValueError("Only automated assignments can start grading jobs")
        assignment = AssignmentConfig(
            name=record.name,
            **record.automated.model_dump(),
        )
        path = self._materialize(record.id, assignment)
        return ApiJobRequest(
            assignment_file=path,
            submissions_dir=Path(launch.submissions_dir),
            no_docker=launch.no_docker,
            workers=launch.workers,
            retries=launch.retries,
            submission_patterns=launch.submission_patterns,
        )

    def _materialize(self, assignment_id: str, assignment: AssignmentConfig) -> Path:
        self.storage_root.mkdir(parents=True, exist_ok=True)
        path = self._path(assignment_id)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("x", encoding="utf-8") as stream:
                yaml.safe_dump(
                    assignment.model_dump(exclude_none=True),
                    stream,
                    sort_keys=False,
                    allow_unicode=True,
                )
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        return path

    def _path(self, assignment_id: str) -> Path:
        return self.storage_root / f"{assignment_id}.yaml"
