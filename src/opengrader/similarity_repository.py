"""SQLite persistence for durable, immutable similarity review reports."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from opengrader.dashboard_contract import validate_job_page
from opengrader.similarity import (
    SimilarityJobRecord,
    SimilarityJobRequest,
    SimilarityJobStatus,
    SimilarityReport,
)


class SimilarityRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> int:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        now = _now_text()
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurred_at TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    details_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS similarity_jobs (
                    id TEXT PRIMARY KEY,
                    assignment_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    submission_ids_json TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    report_json TEXT,
                    error TEXT
                );
                CREATE INDEX IF NOT EXISTS similarity_jobs_assignment_idx
                    ON similarity_jobs(assignment_id, created_at DESC, id DESC);
                CREATE INDEX IF NOT EXISTS similarity_jobs_status_idx
                    ON similarity_jobs(status, created_at, id);
                """
            )
            recovered = connection.execute(
                """
                UPDATE similarity_jobs
                SET status = ?, updated_at = ?, started_at = NULL,
                    error = 'Recovered after worker restart'
                WHERE status = ?
                """,
                (SimilarityJobStatus.QUEUED.value, now, SimilarityJobStatus.RUNNING.value),
            ).rowcount
        return recovered

    def create(
        self,
        request: SimilarityJobRequest,
        *,
        submission_ids: list[str],
        actor: str,
    ) -> SimilarityJobRecord:
        job_id = str(uuid.uuid4())
        now = _now_text()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO similarity_jobs (
                    id, assignment_id, status, request_json, submission_ids_json,
                    created_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    request.assignment_id,
                    SimilarityJobStatus.QUEUED.value,
                    request.model_dump_json(),
                    json.dumps(submission_ids),
                    actor,
                    now,
                    now,
                ),
            )
            self._audit(
                connection,
                actor=actor,
                action="similarity_job.created",
                job_id=job_id,
                details={"assignment_id": request.assignment_id, "submission_count": len(submission_ids)},
                occurred_at=now,
            )
            row = connection.execute("SELECT * FROM similarity_jobs WHERE id = ?", (job_id,)).fetchone()
        return _record(row)

    def get(self, job_id: str) -> SimilarityJobRecord | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM similarity_jobs WHERE id = ?", (job_id,)).fetchone()
        return None if row is None else _record(row)

    def list(
        self,
        *,
        assignment_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SimilarityJobRecord]:
        validate_job_page(limit=limit, offset=offset)
        with self._connect() as connection:
            if assignment_id is None:
                rows = connection.execute(
                    "SELECT * FROM similarity_jobs ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM similarity_jobs WHERE assignment_id = ? ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
                    (assignment_id, limit, offset),
                ).fetchall()
        return [_record(row) for row in rows]

    def claim_next(self, *, worker_actor: str) -> SimilarityJobRecord | None:
        now = _now_text()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT id FROM similarity_jobs WHERE status = ? ORDER BY created_at, id LIMIT 1",
                (SimilarityJobStatus.QUEUED.value,),
            ).fetchone()
            if row is None:
                return None
            job_id = str(row["id"])
            connection.execute(
                "UPDATE similarity_jobs SET status = ?, started_at = ?, updated_at = ?, error = NULL WHERE id = ? AND status = ?",
                (SimilarityJobStatus.RUNNING.value, now, now, job_id, SimilarityJobStatus.QUEUED.value),
            )
            self._audit(connection, actor=worker_actor, action="similarity_job.started", job_id=job_id, details={}, occurred_at=now)
            claimed = connection.execute("SELECT * FROM similarity_jobs WHERE id = ?", (job_id,)).fetchone()
        return _record(claimed)

    def complete(self, job_id: str, *, report: SimilarityReport, worker_actor: str) -> SimilarityJobRecord:
        now = _now_text()
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE similarity_jobs SET status = ?, report_json = ?, completed_at = ?, updated_at = ?, error = NULL WHERE id = ? AND status = ? AND report_json IS NULL",
                (SimilarityJobStatus.SUCCEEDED.value, report.model_dump_json(), now, now, job_id, SimilarityJobStatus.RUNNING.value),
            )
            if cursor.rowcount != 1:
                raise ValueError("Similarity job is not running or already has a report")
            self._audit(connection, actor=worker_actor, action="similarity_job.succeeded", job_id=job_id, details={"match_count": len(report.matches)}, occurred_at=now)
            row = connection.execute("SELECT * FROM similarity_jobs WHERE id = ?", (job_id,)).fetchone()
        return _record(row)

    def fail(self, job_id: str, *, error: str, worker_actor: str) -> SimilarityJobRecord:
        now = _now_text()
        safe_error = error[:2_000]
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE similarity_jobs SET status = ?, error = ?, completed_at = ?, updated_at = ? WHERE id = ? AND status = ?",
                (SimilarityJobStatus.FAILED.value, safe_error, now, now, job_id, SimilarityJobStatus.RUNNING.value),
            )
            if cursor.rowcount != 1:
                raise ValueError("Similarity job is not running")
            self._audit(connection, actor=worker_actor, action="similarity_job.failed", job_id=job_id, details={"error_type": safe_error.split(":", 1)[0]}, occurred_at=now)
            row = connection.execute("SELECT * FROM similarity_jobs WHERE id = ?", (job_id,)).fetchone()
        return _record(row)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @staticmethod
    def _audit(connection: sqlite3.Connection, *, actor: str, action: str, job_id: str, details: dict[str, object], occurred_at: str) -> None:
        connection.execute(
            "INSERT INTO audit_events (occurred_at, actor, action, resource_type, resource_id, details_json) VALUES (?, ?, ?, 'similarity_job', ?, ?)",
            (occurred_at, actor, action, job_id, json.dumps(details, sort_keys=True)),
        )


def _record(row: sqlite3.Row) -> SimilarityJobRecord:
    return SimilarityJobRecord(
        id=row["id"],
        assignment_id=row["assignment_id"],
        status=SimilarityJobStatus(row["status"]),
        request=SimilarityJobRequest.model_validate_json(row["request_json"]),
        submission_ids=json.loads(row["submission_ids_json"]),
        created_by=row["created_by"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
        completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        report=SimilarityReport.model_validate_json(row["report_json"]) if row["report_json"] else None,
        error=row["error"],
    )


def _now_text() -> str:
    return datetime.now(UTC).isoformat()
