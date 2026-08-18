"""SQLite billing projection, webhook ledger, and usage outbox."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from opengrader.billing import (
    BillingAccount,
    BillingSubscriptionUpdate,
    BillingUsageEvent,
    BillingUsageSummary,
    UsageDeliveryStatus,
)
from opengrader.billing_contract import SubscriptionStatus, validate_usage_quantity


class BillingRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS billing_accounts (
                    actor TEXT PRIMARY KEY,
                    customer_id TEXT UNIQUE,
                    subscription_id TEXT UNIQUE,
                    status TEXT NOT NULL,
                    current_period_end TEXT,
                    cancel_at_period_end INTEGER NOT NULL,
                    stripe_event_created INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS stripe_webhook_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    processed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS billing_usage_events (
                    id TEXT PRIMARY KEY,
                    actor TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    last_error TEXT,
                    next_attempt_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    reported_at TEXT,
                    UNIQUE(actor, resource_type, resource_id)
                );
                CREATE INDEX IF NOT EXISTS billing_usage_delivery_idx
                    ON billing_usage_events(status, next_attempt_at, created_at, id);
                """
            )

    def ensure_account(self, actor: str) -> BillingAccount:
        now = _now_text()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO billing_accounts (
                    actor, status, cancel_at_period_end, stripe_event_created,
                    created_at, updated_at
                ) VALUES (?, ?, 0, 0, ?, ?)
                ON CONFLICT(actor) DO NOTHING
                """,
                (actor, SubscriptionStatus.NONE.value, now, now),
            )
            row = connection.execute(
                "SELECT * FROM billing_accounts WHERE actor = ?", (actor,)
            ).fetchone()
        return _account_from_row(row)

    def get_account(self, actor: str) -> BillingAccount | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM billing_accounts WHERE actor = ?", (actor,)
            ).fetchone()
        return None if row is None else _account_from_row(row)

    def actor_for_customer(self, customer_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT actor FROM billing_accounts WHERE customer_id = ?",
                (customer_id,),
            ).fetchone()
        return None if row is None else str(row["actor"])

    def bind_customer(self, actor: str, customer_id: str) -> BillingAccount:
        self.ensure_account(actor)
        now = _now_text()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE billing_accounts
                SET customer_id = ?, updated_at = ? WHERE actor = ?
                """,
                (customer_id, now, actor),
            )
        account = self.get_account(actor)
        if account is None:
            raise RuntimeError("billing account disappeared")
        return account

    def apply_subscription_event(
        self,
        *,
        event_id: str,
        event_type: str,
        update: BillingSubscriptionUpdate,
    ) -> bool:
        now = _now_text()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if not self._register_event(
                connection, event_id=event_id, event_type=event_type, processed_at=now
            ):
                connection.commit()
                return False
            connection.execute(
                """
                INSERT INTO billing_accounts (
                    actor, customer_id, subscription_id, status,
                    current_period_end, cancel_at_period_end,
                    stripe_event_created, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(actor) DO UPDATE SET
                    customer_id = excluded.customer_id,
                    subscription_id = excluded.subscription_id,
                    status = excluded.status,
                    current_period_end = excluded.current_period_end,
                    cancel_at_period_end = excluded.cancel_at_period_end,
                    stripe_event_created = excluded.stripe_event_created,
                    updated_at = excluded.updated_at
                WHERE excluded.stripe_event_created >= billing_accounts.stripe_event_created
                """,
                (
                    update.actor,
                    update.customer_id,
                    update.subscription_id,
                    update.status.value,
                    _datetime_text(update.current_period_end),
                    int(update.cancel_at_period_end),
                    update.stripe_event_created,
                    now,
                    now,
                ),
            )
            connection.commit()
        return True

    def apply_checkout_event(
        self,
        *,
        event_id: str,
        event_type: str,
        actor: str,
        customer_id: str,
        subscription_id: str | None,
    ) -> bool:
        now = _now_text()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if not self._register_event(
                connection, event_id=event_id, event_type=event_type, processed_at=now
            ):
                connection.commit()
                return False
            connection.execute(
                """
                INSERT INTO billing_accounts (
                    actor, customer_id, subscription_id, status,
                    cancel_at_period_end, stripe_event_created, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 0, 0, ?, ?)
                ON CONFLICT(actor) DO UPDATE SET
                    customer_id = excluded.customer_id,
                    subscription_id = COALESCE(
                        excluded.subscription_id, billing_accounts.subscription_id
                    ),
                    updated_at = excluded.updated_at
                """,
                (
                    actor,
                    customer_id,
                    subscription_id,
                    SubscriptionStatus.NONE.value,
                    now,
                    now,
                ),
            )
            connection.commit()
        return True

    def record_webhook_event(self, *, event_id: str, event_type: str) -> bool:
        with self._connect() as connection:
            return self._register_event(
                connection,
                event_id=event_id,
                event_type=event_type,
                processed_at=_now_text(),
            )

    def webhook_event_count(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM stripe_webhook_events"
            ).fetchone()
        return int(row["count"])

    def record_usage(
        self,
        *,
        actor: str,
        resource_type: str,
        resource_id: str,
        quantity: int = 1,
    ) -> BillingUsageEvent:
        quantity = validate_usage_quantity(quantity)
        now = _now_text()
        usage_id = str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO billing_usage_events (
                    id, actor, resource_type, resource_id, quantity, status,
                    attempts, next_attempt_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
                ON CONFLICT(actor, resource_type, resource_id) DO NOTHING
                """,
                (
                    usage_id,
                    actor,
                    resource_type,
                    resource_id,
                    quantity,
                    UsageDeliveryStatus.PENDING.value,
                    now,
                    now,
                ),
            )
            row = connection.execute(
                """
                SELECT usage.*, account.customer_id
                FROM billing_usage_events AS usage
                LEFT JOIN billing_accounts AS account ON account.actor = usage.actor
                WHERE usage.actor = ? AND usage.resource_type = ? AND usage.resource_id = ?
                """,
                (actor, resource_type, resource_id),
            ).fetchone()
        return _usage_from_row(row)

    def next_reportable_usage(self) -> BillingUsageEvent | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT usage.*, account.customer_id
                FROM billing_usage_events AS usage
                JOIN billing_accounts AS account ON account.actor = usage.actor
                WHERE usage.status IN (?, ?)
                  AND usage.next_attempt_at <= ?
                  AND account.customer_id IS NOT NULL
                  AND account.status IN (?, ?)
                ORDER BY usage.created_at, usage.id
                LIMIT 1
                """,
                (
                    UsageDeliveryStatus.PENDING.value,
                    UsageDeliveryStatus.FAILED.value,
                    _now_text(),
                    SubscriptionStatus.ACTIVE.value,
                    SubscriptionStatus.TRIALING.value,
                ),
            ).fetchone()
        return None if row is None else _usage_from_row(row)

    def mark_usage_reported(self, usage_id: str) -> None:
        now = _now_text()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE billing_usage_events
                SET status = ?, reported_at = ?, last_error = NULL
                WHERE id = ? AND status != ?
                """,
                (
                    UsageDeliveryStatus.REPORTED.value,
                    now,
                    usage_id,
                    UsageDeliveryStatus.REPORTED.value,
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"Usage event '{usage_id}' is not reportable")

    def mark_usage_failed(
        self, usage_id: str, error: str, *, retry_after_seconds: float = 0
    ) -> None:
        next_attempt = datetime.now(UTC) + timedelta(seconds=retry_after_seconds)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE billing_usage_events
                SET status = ?, attempts = attempts + 1, last_error = ?,
                    next_attempt_at = ?
                WHERE id = ? AND status != ?
                """,
                (
                    UsageDeliveryStatus.FAILED.value,
                    error[:1000],
                    next_attempt.isoformat(),
                    usage_id,
                    UsageDeliveryStatus.REPORTED.value,
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"Usage event '{usage_id}' is not reportable")

    def usage_summary(self, actor: str) -> BillingUsageSummary:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT status, COALESCE(SUM(quantity), 0) AS units
                FROM billing_usage_events WHERE actor = ? GROUP BY status
                """,
                (actor,),
            ).fetchall()
        units = {str(row["status"]): int(row["units"]) for row in rows}
        reported = units.get(UsageDeliveryStatus.REPORTED.value, 0)
        pending = sum(units.values()) - reported
        return BillingUsageSummary(
            total_units=sum(units.values()),
            reported_units=reported,
            pending_units=pending,
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @staticmethod
    def _register_event(
        connection: sqlite3.Connection,
        *,
        event_id: str,
        event_type: str,
        processed_at: str,
    ) -> bool:
        cursor = connection.execute(
            """
            INSERT INTO stripe_webhook_events (event_id, event_type, processed_at)
            VALUES (?, ?, ?) ON CONFLICT(event_id) DO NOTHING
            """,
            (event_id, event_type, processed_at),
        )
        return cursor.rowcount == 1


def _account_from_row(row: sqlite3.Row) -> BillingAccount:
    return BillingAccount(
        actor=row["actor"],
        customer_id=row["customer_id"],
        subscription_id=row["subscription_id"],
        status=SubscriptionStatus(row["status"]),
        current_period_end=(
            datetime.fromisoformat(row["current_period_end"])
            if row["current_period_end"]
            else None
        ),
        cancel_at_period_end=bool(row["cancel_at_period_end"]),
        stripe_event_created=row["stripe_event_created"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _usage_from_row(row: sqlite3.Row) -> BillingUsageEvent:
    return BillingUsageEvent(
        id=row["id"],
        actor=row["actor"],
        resource_type=row["resource_type"],
        resource_id=row["resource_id"],
        quantity=row["quantity"],
        status=UsageDeliveryStatus(row["status"]),
        attempts=row["attempts"],
        last_error=row["last_error"],
        created_at=datetime.fromisoformat(row["created_at"]),
        reported_at=(
            datetime.fromisoformat(row["reported_at"]) if row["reported_at"] else None
        ),
        customer_id=row["customer_id"],
    )


def _datetime_text(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _now_text() -> str:
    return datetime.now(UTC).isoformat()

