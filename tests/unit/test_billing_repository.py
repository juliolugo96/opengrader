from datetime import UTC, datetime, timedelta

import pytest

from opengrader.billing import BillingSubscriptionUpdate, UsageDeliveryStatus
from opengrader.billing_contract import SubscriptionStatus
from opengrader.billing_repository import BillingRepository

pytestmark = pytest.mark.unit


def subscription_update(*, status=SubscriptionStatus.ACTIVE, created=200):
    return BillingSubscriptionUpdate(
        actor="key:tenant",
        customer_id="cus_123",
        subscription_id="sub_123",
        status=status,
        current_period_end=datetime(2026, 9, 18, tzinfo=UTC),
        cancel_at_period_end=False,
        stripe_event_created=created,
    )


def test_subscription_projection_is_idempotent_and_ordered(tmp_path) -> None:
    repository = BillingRepository(tmp_path / "jobs.db")
    repository.initialize()

    assert repository.apply_subscription_event(
        event_id="evt_new", event_type="customer.subscription.updated",
        update=subscription_update(),
    ) is True
    assert repository.apply_subscription_event(
        event_id="evt_new", event_type="customer.subscription.updated",
        update=subscription_update(),
    ) is False
    assert repository.apply_subscription_event(
        event_id="evt_old", event_type="customer.subscription.deleted",
        update=subscription_update(status=SubscriptionStatus.CANCELED, created=100),
    ) is True

    account = repository.get_account("key:tenant")
    assert account is not None
    assert account.status is SubscriptionStatus.ACTIVE
    assert account.customer_id == "cus_123"
    assert repository.webhook_event_count() == 2


def test_checkout_binding_and_usage_outbox_are_separate_and_deduplicated(tmp_path) -> None:
    repository = BillingRepository(tmp_path / "jobs.db")
    repository.initialize()
    repository.bind_customer("key:tenant", "cus_123")
    repository.apply_subscription_event(
        event_id="evt_active", event_type="customer.subscription.created",
        update=subscription_update(),
    )

    first = repository.record_usage(
        actor="key:tenant", resource_type="job", resource_id="job-1", quantity=2
    )
    duplicate = repository.record_usage(
        actor="key:tenant", resource_type="job", resource_id="job-1", quantity=2
    )
    pdf = repository.record_usage(
        actor="key:tenant", resource_type="pdf_submission", resource_id="pdf-1"
    )

    assert duplicate.id == first.id
    assert repository.next_reportable_usage() == first
    repository.mark_usage_failed(first.id, "temporary Stripe failure")
    retried = repository.next_reportable_usage()
    assert retried is not None and retried.id == first.id and retried.attempts == 1
    repository.mark_usage_reported(first.id)
    assert repository.next_reportable_usage() == pdf

    summary = repository.usage_summary("key:tenant")
    assert summary.total_units == 3
    assert summary.reported_units == 2
    assert summary.pending_units == 1
    assert first.status is UsageDeliveryStatus.PENDING


def test_usage_is_not_reportable_without_an_entitled_customer(tmp_path) -> None:
    repository = BillingRepository(tmp_path / "jobs.db")
    repository.initialize()
    repository.record_usage(
        actor="key:tenant", resource_type="job", resource_id="job-1"
    )

    assert repository.next_reportable_usage() is None

