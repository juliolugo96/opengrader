"""SQLite persistence for API jobs and append-only audit events."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from opengrader.api_models import (
    ApiJobRequest,
    AuditEvent,
    JobRecord,
    JobStatus,
)
from opengrader.dashboard_contract import validate_job_page
from opengrader.results import GradingResult


class JobRepository:
    """Small connection-per-operation repository safe for worker threads."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> int:
        """Create schema and requeue jobs interrupted by a prior process."""

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    result_json TEXT,
                    reports_json TEXT,
                    error TEXT
                );
                CREATE INDEX IF NOT EXISTS jobs_status_created_idx
                    ON jobs(status, created_at, id);
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurred_at TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    details_json TEXT NOT NULL
                );
                """
            )
            running_ids = [
                row["id"]
                for row in connection.execute(
                    "SELECT id FROM jobs WHERE status = ? ORDER BY created_at, id",
                    (JobStatus.RUNNING.value,),
                ).fetchall()
            ]
            now = _now_text()
            for job_id in running_ids:
                connection.execute(
                    """
                    UPDATE jobs
                    SET status = ?, updated_at = ?, started_at = NULL, error = NULL
                    WHERE id = ?
                    """,
                    (JobStatus.QUEUED.value, now, job_id),
                )
                self._insert_audit(
                    connection,
                    actor="system:recovery",
                    action="job.requeued",
                    resource_id=job_id,
                    details={},
                    occurred_at=now,
                )
        return len(running_ids)

    def create_job(self, request: ApiJobRequest, actor: str) -> JobRecord:
        job_id = str(uuid.uuid4())
        now = _now_text()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    id, status, request_json, created_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    JobStatus.QUEUED.value,
                    request.model_dump_json(),
                    actor,
                    now,
                    now,
                ),
            )
            self._insert_audit(
                connection,
                actor=actor,
                action="job.created",
                resource_id=job_id,
                details={"status": JobStatus.QUEUED.value},
                occurred_at=now,
            )
            row = connection.execute(
                "SELECT * FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
        return _job_from_row(row)

    def claim_next_job(self, worker_actor: str) -> JobRecord | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            queued = connection.execute(
                """
                SELECT id FROM jobs
                WHERE status = ?
                ORDER BY created_at, id
                LIMIT 1
                """,
                (JobStatus.QUEUED.value,),
            ).fetchone()
            if queued is None:
                connection.commit()
                return None

            now = _now_text()
            connection.execute(
                """
                UPDATE jobs
                SET status = ?, updated_at = ?, started_at = ?
                WHERE id = ? AND status = ?
                """,
                (
                    JobStatus.RUNNING.value,
                    now,
                    now,
                    queued["id"],
                    JobStatus.QUEUED.value,
                ),
            )
            self._insert_audit(
                connection,
                actor=worker_actor,
                action="job.started",
                resource_id=queued["id"],
                details={"status": JobStatus.RUNNING.value},
                occurred_at=now,
            )
            row = connection.execute(
                "SELECT * FROM jobs WHERE id = ?", (queued["id"],)
            ).fetchone()
            connection.commit()
        return _job_from_row(row)

    def complete_job(
        self,
        job_id: str,
        *,
        result: GradingResult,
        reports: dict[str, str],
        worker_actor: str,
    ) -> None:
        now = _now_text()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE jobs
                SET status = ?, updated_at = ?, completed_at = ?,
                    result_json = ?, reports_json = ?, error = NULL
                WHERE id = ? AND status = ?
                """,
                (
                    JobStatus.SUCCEEDED.value,
                    now,
                    now,
                    result.model_dump_json(exclude_computed_fields=True),
                    json.dumps(reports, sort_keys=True),
                    job_id,
                    JobStatus.RUNNING.value,
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"Job '{job_id}' is not running")
            self._insert_audit(
                connection,
                actor=worker_actor,
                action="job.succeeded",
                resource_id=job_id,
                details={"status": JobStatus.SUCCEEDED.value},
                occurred_at=now,
            )

    def fail_job(self, job_id: str, *, error: str, worker_actor: str) -> None:
        now = _now_text()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE jobs
                SET status = ?, updated_at = ?, completed_at = ?, error = ?
                WHERE id = ? AND status = ?
                """,
                (
                    JobStatus.FAILED.value,
                    now,
                    now,
                    error,
                    job_id,
                    JobStatus.RUNNING.value,
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"Job '{job_id}' is not running")
            self._insert_audit(
                connection,
                actor=worker_actor,
                action="job.failed",
                resource_id=job_id,
                details={"status": JobStatus.FAILED.value},
                occurred_at=now,
            )

    def get_job(self, job_id: str) -> JobRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
        return None if row is None else _job_from_row(row)

    def list_jobs(
        self, *, status: JobStatus | None = None, limit: int = 50, offset: int = 0
    ) -> list[JobRecord]:
        validate_job_page(limit=limit, offset=offset)
        with self._connect() as connection:
            if status is None:
                rows = connection.execute(
                    """
                    SELECT * FROM jobs
                    ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM jobs WHERE status = ?
                    ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?
                    """,
                    (status.value, limit, offset),
                ).fetchall()
        return [_job_from_row(row) for row in rows]

    def list_audit_events(self, *, limit: int = 100) -> list[AuditEvent]:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM audit_events ORDER BY id ASC LIMIT ?", (limit,)
            ).fetchall()
        return [_audit_from_row(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @staticmethod
    def _insert_audit(
        connection: sqlite3.Connection,
        *,
        actor: str,
        action: str,
        resource_id: str,
        details: dict[str, object],
        occurred_at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO audit_events (
                occurred_at, actor, action, resource_type, resource_id, details_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                occurred_at,
                actor,
                action,
                "job",
                resource_id,
                json.dumps(details, sort_keys=True),
            ),
        )


def _job_from_row(row: sqlite3.Row) -> JobRecord:
    return JobRecord(
        id=row["id"],
        status=JobStatus(row["status"]),
        request=ApiJobRequest.model_validate_json(row["request_json"]),
        created_by=row["created_by"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        started_at=(
            datetime.fromisoformat(row["started_at"]) if row["started_at"] else None
        ),
        completed_at=(
            datetime.fromisoformat(row["completed_at"])
            if row["completed_at"]
            else None
        ),
        result=(
            GradingResult.model_validate_json(row["result_json"])
            if row["result_json"]
            else None
        ),
        reports=json.loads(row["reports_json"]) if row["reports_json"] else {},
        error=row["error"],
    )


def _audit_from_row(row: sqlite3.Row) -> AuditEvent:
    return AuditEvent(
        id=row["id"],
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        actor=row["actor"],
        action=row["action"],
        resource_type=row["resource_type"],
        resource_id=row["resource_id"],
        details=json.loads(row["details_json"]),
    )


def _now_text() -> str:
    return datetime.now(UTC).isoformat()
