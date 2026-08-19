"""SQLite persistence for professor-created academic assignments."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from opengrader.academic import (
    AcademicAssignmentCreate,
    AcademicAssignmentRecord,
    AcademicContext,
    AssignmentKind,
    AutomatedAssignmentDefinition,
)
from opengrader.mvp4_contract import validate_job_page


class AcademicAssignmentRepository:
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
                CREATE TABLE IF NOT EXISTS academic_assignments (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    institution TEXT NOT NULL,
                    course_code TEXT NOT NULL,
                    course_name TEXT NOT NULL,
                    academic_period TEXT NOT NULL,
                    section TEXT NOT NULL,
                    automated_json TEXT,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS academic_assignments_context_idx
                    ON academic_assignments(
                        institution, course_code, academic_period, section, name
                    );
                """
            )

    def create(
        self, request: AcademicAssignmentCreate, *, actor: str
    ) -> AcademicAssignmentRecord:
        assignment_id = str(uuid.uuid4())
        now = _now_text()
        with self._connect() as connection:
            self._write(
                connection,
                assignment_id=assignment_id,
                request=request,
                actor=actor,
                created_at=now,
                updated_at=now,
            )
            self._insert_audit(
                connection,
                actor=actor,
                action="academic_assignment.created",
                assignment_id=assignment_id,
                details={"kind": request.kind.value},
                occurred_at=now,
            )
            row = connection.execute(
                "SELECT * FROM academic_assignments WHERE id = ?", (assignment_id,)
            ).fetchone()
        return _record_from_row(row)

    def update(
        self,
        assignment_id: str,
        request: AcademicAssignmentCreate,
        *,
        actor: str,
    ) -> AcademicAssignmentRecord:
        current = self.get(assignment_id)
        if current is None:
            raise KeyError(assignment_id)
        now = _now_text()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE academic_assignments SET
                    name = ?, kind = ?, institution = ?, course_code = ?,
                    course_name = ?, academic_period = ?, section = ?,
                    automated_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (*_request_values(request), now, assignment_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(assignment_id)
            self._insert_audit(
                connection,
                actor=actor,
                action="academic_assignment.updated",
                assignment_id=assignment_id,
                details={"kind": request.kind.value},
                occurred_at=now,
            )
            row = connection.execute(
                "SELECT * FROM academic_assignments WHERE id = ?", (assignment_id,)
            ).fetchone()
        return _record_from_row(row)

    def delete(self, assignment_id: str, *, actor: str) -> bool:
        now = _now_text()
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM academic_assignments WHERE id = ?", (assignment_id,)
            )
            if cursor.rowcount != 1:
                return False
            self._insert_audit(
                connection,
                actor=actor,
                action="academic_assignment.deleted",
                assignment_id=assignment_id,
                details={},
                occurred_at=now,
            )
        return True

    def get(self, assignment_id: str) -> AcademicAssignmentRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM academic_assignments WHERE id = ?", (assignment_id,)
            ).fetchone()
        return None if row is None else _record_from_row(row)

    def list(
        self,
        *,
        institution: str | None = None,
        course_code: str | None = None,
        period: str | None = None,
        section: str | None = None,
        kind: AssignmentKind | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AcademicAssignmentRecord]:
        validate_job_page(limit=limit, offset=offset)
        filters: list[str] = []
        values: list[object] = []
        for column, value in (
            ("institution", institution),
            ("course_code", course_code),
            ("academic_period", period),
            ("section", section),
        ):
            if value is not None:
                filters.append(f"{column} = ?")
                values.append(value)
        if kind is not None:
            filters.append("kind = ?")
            values.append(kind.value)
        where = f"WHERE {' AND '.join(filters)}" if filters else ""
        values.extend((limit, offset))
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM academic_assignments {where}
                ORDER BY institution, course_code, academic_period, section,
                         name, created_at, id
                LIMIT ? OFFSET ?
                """,
                values,
            ).fetchall()
        return [_record_from_row(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @staticmethod
    def _write(
        connection: sqlite3.Connection,
        *,
        assignment_id: str,
        request: AcademicAssignmentCreate,
        actor: str,
        created_at: str,
        updated_at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO academic_assignments (
                id, name, kind, institution, course_code, course_name,
                academic_period, section, automated_json, created_by,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                assignment_id,
                *_request_values(request),
                actor,
                created_at,
                updated_at,
            ),
        )

    @staticmethod
    def _insert_audit(
        connection: sqlite3.Connection,
        *,
        actor: str,
        action: str,
        assignment_id: str,
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
                "academic_assignment",
                assignment_id,
                json.dumps(details, sort_keys=True),
            ),
        )


def _request_values(request: AcademicAssignmentCreate) -> tuple[object, ...]:
    return (
        request.name,
        request.kind.value,
        request.context.institution,
        request.context.course_code,
        request.context.course_name,
        request.context.period,
        request.context.section,
        request.automated.model_dump_json() if request.automated else None,
    )


def _record_from_row(row: sqlite3.Row) -> AcademicAssignmentRecord:
    return AcademicAssignmentRecord(
        id=row["id"],
        name=row["name"],
        kind=AssignmentKind(row["kind"]),
        context=AcademicContext(
            institution=row["institution"],
            course_code=row["course_code"],
            course_name=row["course_name"],
            period=row["academic_period"],
            section=row["section"],
        ),
        automated=(
            AutomatedAssignmentDefinition.model_validate_json(row["automated_json"])
            if row["automated_json"]
            else None
        ),
        created_by=row["created_by"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _now_text() -> str:
    return datetime.now(UTC).isoformat()
