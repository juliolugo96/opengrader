"""SQLite persistence for manual PDF grading records."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from opengrader.api_models import AuditEvent
from opengrader.mvp4_contract import validate_job_page
from opengrader.pdf_grading import (
    PdfGradeRequest,
    PdfSubmissionRecord,
    PdfSubmissionStatus,
)


class PdfSubmissionRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
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
                CREATE TABLE IF NOT EXISTS pdf_submissions (
                    id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    page_count INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    grade_json TEXT,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    finalized_at TEXT
                );
                CREATE INDEX IF NOT EXISTS pdf_submissions_created_idx
                    ON pdf_submissions(created_at, id);
                """
            )

    def create_submission(
        self,
        *,
        submission_id: str,
        student_id: str,
        title: str,
        original_filename: str,
        size_bytes: int,
        sha256: str,
        page_count: int,
        actor: str,
    ) -> PdfSubmissionRecord:
        if page_count < 1:
            raise ValueError("page_count must be positive")
        if size_bytes < 1:
            raise ValueError("size_bytes must be positive")
        now = _now_text()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO pdf_submissions (
                    id, student_id, title, original_filename, size_bytes, sha256,
                    page_count, status, created_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    submission_id,
                    student_id,
                    title,
                    original_filename,
                    size_bytes,
                    sha256,
                    page_count,
                    PdfSubmissionStatus.DRAFT.value,
                    actor,
                    now,
                    now,
                ),
            )
            self._insert_audit(
                connection,
                actor=actor,
                action="pdf_submission.created",
                resource_id=submission_id,
                details={"page_count": page_count, "size_bytes": size_bytes},
                occurred_at=now,
            )
            row = connection.execute(
                "SELECT * FROM pdf_submissions WHERE id = ?", (submission_id,)
            ).fetchone()
        return _record_from_row(row)

    def get_submission(self, submission_id: str) -> PdfSubmissionRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM pdf_submissions WHERE id = ?", (submission_id,)
            ).fetchone()
        return None if row is None else _record_from_row(row)

    def list_submissions(
        self, *, limit: int = 50, offset: int = 0
    ) -> list[PdfSubmissionRecord]:
        validate_job_page(limit=limit, offset=offset)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM pdf_submissions
                ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [_record_from_row(row) for row in rows]

    def save_grade(
        self, submission_id: str, *, grade: PdfGradeRequest, actor: str
    ) -> PdfSubmissionRecord:
        current = self.get_submission(submission_id)
        if current is None:
            raise KeyError(submission_id)
        if current.status is PdfSubmissionStatus.FINALIZED:
            raise ValueError("Finalized PDF grades cannot be changed")

        now = _now_text()
        status = (
            PdfSubmissionStatus.FINALIZED
            if grade.finalized
            else PdfSubmissionStatus.DRAFT
        )
        finalized_at = now if grade.finalized else None
        action = (
            "pdf_submission.finalized"
            if grade.finalized
            else "pdf_submission.grade_saved"
        )
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE pdf_submissions
                SET status = ?, grade_json = ?, updated_at = ?, finalized_at = ?
                WHERE id = ? AND status = ?
                """,
                (
                    status.value,
                    grade.model_dump_json(),
                    now,
                    finalized_at,
                    submission_id,
                    PdfSubmissionStatus.DRAFT.value,
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError("Finalized PDF grades cannot be changed")
            self._insert_audit(
                connection,
                actor=actor,
                action=action,
                resource_id=submission_id,
                details={
                    "status": status.value,
                    "total_score": grade.total_score,
                    "maximum_points": grade.maximum_points,
                },
                occurred_at=now,
            )
            row = connection.execute(
                "SELECT * FROM pdf_submissions WHERE id = ?", (submission_id,)
            ).fetchone()
        return _record_from_row(row)

    def list_audit_events(self) -> list[AuditEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM audit_events
                WHERE resource_type = 'pdf_submission' ORDER BY id ASC
                """
            ).fetchall()
        return [
            AuditEvent(
                id=row["id"],
                occurred_at=datetime.fromisoformat(row["occurred_at"]),
                actor=row["actor"],
                action=row["action"],
                resource_type=row["resource_type"],
                resource_id=row["resource_id"],
                details=json.loads(row["details_json"]),
            )
            for row in rows
        ]

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
                "pdf_submission",
                resource_id,
                json.dumps(details, sort_keys=True),
            ),
        )


def _record_from_row(row: sqlite3.Row) -> PdfSubmissionRecord:
    return PdfSubmissionRecord(
        id=row["id"],
        student_id=row["student_id"],
        title=row["title"],
        original_filename=row["original_filename"],
        size_bytes=row["size_bytes"],
        sha256=row["sha256"],
        page_count=row["page_count"],
        status=PdfSubmissionStatus(row["status"]),
        grade=(
            PdfGradeRequest.model_validate_json(row["grade_json"])
            if row["grade_json"]
            else None
        ),
        created_by=row["created_by"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        finalized_at=(
            datetime.fromisoformat(row["finalized_at"])
            if row["finalized_at"]
            else None
        ),
    )


def _now_text() -> str:
    return datetime.now(UTC).isoformat()
