"""Durable LMS assignment links and idempotent grade deliveries."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from opengrader.lms import LmsAssignmentLinkRecord, LmsProvider


class LmsRepository:
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
                CREATE TABLE IF NOT EXISTS lms_assignment_links (
                    id TEXT PRIMARY KEY,
                    local_assignment_id TEXT NOT NULL UNIQUE,
                    provider TEXT NOT NULL,
                    external_course_id TEXT NOT NULL,
                    external_assignment_id TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(provider, external_course_id, external_assignment_id)
                );
                CREATE INDEX IF NOT EXISTS lms_links_provider_idx
                    ON lms_assignment_links(provider, external_course_id, external_assignment_id);
                CREATE TABLE IF NOT EXISTS lms_grade_deliveries (
                    delivery_key TEXT PRIMARY KEY,
                    link_id TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    posted_grade TEXT NOT NULL,
                    source_revision TEXT NOT NULL,
                    delivered_by TEXT NOT NULL,
                    delivered_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS lms_deliveries_link_idx
                    ON lms_grade_deliveries(link_id, delivered_at);
                """
            )

    def create_link(
        self,
        *,
        local_assignment_id: str,
        provider: LmsProvider,
        external_course_id: str,
        external_assignment_id: str,
        actor: str,
    ) -> LmsAssignmentLinkRecord:
        link_id = str(uuid.uuid4())
        now = _now_text()
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO lms_assignment_links (
                        id, local_assignment_id, provider, external_course_id,
                        external_assignment_id, created_by, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        link_id, local_assignment_id, provider.value,
                        external_course_id, external_assignment_id, actor, now, now,
                    ),
                )
                self._insert_audit(
                    connection, actor=actor, action="lms_assignment.linked",
                    resource_id=link_id,
                    details={
                        "provider": provider.value,
                        "local_assignment_id": local_assignment_id,
                        "external_course_id": external_course_id,
                        "external_assignment_id": external_assignment_id,
                    },
                    occurred_at=now,
                )
                row = connection.execute(
                    "SELECT * FROM lms_assignment_links WHERE id = ?", (link_id,)
                ).fetchone()
        except sqlite3.IntegrityError as exc:
            raise ValueError("The local or remote assignment is already linked") from exc
        return _link_from_row(row)

    def get_link(self, local_assignment_id: str) -> LmsAssignmentLinkRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM lms_assignment_links WHERE local_assignment_id = ?",
                (local_assignment_id,),
            ).fetchone()
        return None if row is None else _link_from_row(row)

    def list_links(self) -> list[LmsAssignmentLinkRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM lms_assignment_links ORDER BY created_at, id"
            ).fetchall()
        return [_link_from_row(row) for row in rows]

    def delete_link(self, local_assignment_id: str, *, actor: str) -> bool:
        now = _now_text()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id FROM lms_assignment_links WHERE local_assignment_id = ?",
                (local_assignment_id,),
            ).fetchone()
            if row is None:
                return False
            connection.execute(
                "DELETE FROM lms_assignment_links WHERE local_assignment_id = ?",
                (local_assignment_id,),
            )
            self._insert_audit(
                connection, actor=actor, action="lms_assignment.unlinked",
                resource_id=row["id"], details={"local_assignment_id": local_assignment_id},
                occurred_at=now,
            )
        return True

    def was_delivered(self, delivery_key: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM lms_grade_deliveries WHERE delivery_key = ?",
                (delivery_key,),
            ).fetchone()
        return row is not None

    def record_delivery(
        self,
        *,
        delivery_key: str,
        link_id: str,
        student_id: str,
        posted_grade: str,
        source_revision: str,
        actor: str,
    ) -> None:
        now = _now_text()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO lms_grade_deliveries (
                    delivery_key, link_id, student_id, posted_grade,
                    source_revision, delivered_by, delivered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    delivery_key, link_id, student_id, posted_grade,
                    source_revision, actor, now,
                ),
            )
            if cursor.rowcount == 1:
                self._insert_audit(
                    connection, actor=actor, action="lms_grade.delivered",
                    resource_id=delivery_key,
                    details={
                        "link_id": link_id, "student_id": student_id,
                        "posted_grade": posted_grade, "source_revision": source_revision,
                    },
                    occurred_at=now,
                )

    def delivery_count(self) -> int:
        with self._connect() as connection:
            return int(
                connection.execute("SELECT COUNT(*) FROM lms_grade_deliveries").fetchone()[0]
            )

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
                occurred_at, actor, action, "lms_integration", resource_id,
                json.dumps(details, sort_keys=True),
            ),
        )


def _link_from_row(row: sqlite3.Row) -> LmsAssignmentLinkRecord:
    return LmsAssignmentLinkRecord(
        id=row["id"], local_assignment_id=row["local_assignment_id"],
        provider=LmsProvider(row["provider"]),
        external_course_id=row["external_course_id"],
        external_assignment_id=row["external_assignment_id"],
        created_by=row["created_by"], created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _now_text() -> str:
    return datetime.now(UTC).isoformat()
