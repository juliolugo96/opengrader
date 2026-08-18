from datetime import UTC, datetime

import pytest

from opengrader.billing import BillingMode, BillingSubscriptionUpdate
from opengrader.billing_contract import SubscriptionStatus
from opengrader.billing_repository import BillingRepository
from opengrader.billing_service import (
    BillingNotConfigured,
    BillingRequired,
    BillingService,
    BillingUsageWorker,
)

pytestmark = pytest.mark.unit


class FakeStripeGateway:
    def __init__(self) -> None:
        self.customers = []
        self.checkout_sessions = []
        self.portal_sessions = []
        self.meter_events = []
        self.event = None
        self.fail_metering = False

    def create_customer(self, *, actor: str, email: str) -> str:
        self.customers.append((actor, email))
        return "cus_test"

    def create_checkout_session(self, *, actor: str, customer_id: str) -> str:
        self.checkout_sessions.append((actor, customer_id))
        return "https://checkout.stripe.test/session"

    def create_portal_session(self, *, customer_id: str) -> str:
        self.portal_sessions.append(customer_id)
        return "https://billing.stripe.test/portal"

    def construct_webhook_event(self, payload: bytes, signature: str, secret: str):
        if (
            signature != "valid-signature"
            or secret != "whsec_test"
            or self.event is None
        ):
            raise ValueError("invalid Stripe signature")
        return self.event

    def report_usage(self, *, event_name, customer_id, usage):
        if self.fail_metering:
            raise RuntimeError("Stripe unavailable")
        self.meter_events.append((event_name, customer_id, usage))


def service(tmp_path, *, enabled=True):
    repository = BillingRepository(tmp_path / "jobs.db")
    repository.initialize()
    gateway = FakeStripeGateway()
    billing = BillingService(
        repository,
        enabled=enabled,
        gateway=gateway if enabled else None,
        webhook_secret="whsec_test" if enabled else None,
        price_id="price_test" if enabled else None,
        meter_event_name="opengrader_grading_units",
    )
    return billing, repository, gateway


def test_local_mode_is_free_and_does_not_require_stripe(tmp_path) -> None:
    billing, _, _ = service(tmp_path, enabled=False)

    assert billing.overview("key:local").mode is BillingMode.LOCAL
    assert billing.overview("key:local").entitled is True
    assert billing.require_entitlement("key:local") is None
    with pytest.raises(BillingNotConfigured):
        billing.create_checkout("key:local", email="teacher@example.com")


def test_hosted_checkout_portal_and_entitlements_use_durable_account_state(tmp_path) -> None:
    billing, repository, gateway = service(tmp_path)

    with pytest.raises(BillingRequired):
        billing.require_entitlement("key:tenant")
    checkout = billing.create_checkout("key:tenant", email="teacher@example.com")
    assert checkout.url.startswith("https://checkout.stripe.test/")
    assert gateway.customers == [("key:tenant", "teacher@example.com")]
    assert repository.get_account("key:tenant").customer_id == "cus_test"

    repository.apply_subscription_event(
        event_id="evt_active", event_type="customer.subscription.created",
        update=BillingSubscriptionUpdate(
            actor="key:tenant", customer_id="cus_test", subscription_id="sub_test",
            status=SubscriptionStatus.ACTIVE, current_period_end=None,
            cancel_at_period_end=False, stripe_event_created=100,
        ),
    )
    assert billing.require_entitlement("key:tenant") is None
    assert billing.create_portal("key:tenant").url.endswith("/portal")
    with pytest.raises(BillingRequired, match="existing subscription"):
        billing.create_checkout("key:tenant", email="teacher@example.com")


def test_verified_webhooks_are_idempotent_and_update_subscription_state(tmp_path) -> None:
    billing, repository, gateway = service(tmp_path)
    gateway.event = {
        "id": "evt_123", "type": "customer.subscription.updated", "created": 200,
        "data": {"object": {
            "id": "sub_123", "customer": "cus_123", "status": "trialing",
            "cancel_at_period_end": True,
            "metadata": {"opengrader_actor": "key:tenant"},
            "items": {"data": [{
                "price": {"id": "price_test"},
                "current_period_end": 1789689600,
            }]},
        }},
    }

    assert billing.handle_webhook(b"raw", "valid-signature") is True
    assert billing.handle_webhook(b"raw", "valid-signature") is False
    account = repository.get_account("key:tenant")
    assert account.status is SubscriptionStatus.TRIALING
    assert account.cancel_at_period_end is True
    assert account.current_period_end == datetime(2026, 9, 18, tzinfo=UTC)


@pytest.mark.parametrize(
    "event_type", ["customer.subscription.created", "customer.subscription.deleted"]
)
def test_subscription_for_a_different_price_does_not_change_access(
    tmp_path, event_type
) -> None:
    billing, repository, gateway = service(tmp_path)
    gateway.event = {
        "id": "evt_wrong_price", "type": event_type, "created": 200,
        "data": {"object": {
            "id": "sub_wrong", "customer": "cus_wrong", "status": "active",
            "metadata": {"opengrader_actor": "key:tenant"},
            "items": {"data": [{"price": {"id": "price_other"}}]},
        }},
    }

    assert billing.handle_webhook(b"raw", "valid-signature") is True
    assert repository.get_account("key:tenant") is None
    with pytest.raises(BillingRequired):
        billing.require_entitlement("key:tenant")


def test_usage_worker_retries_with_the_same_durable_identifier(tmp_path) -> None:
    billing, repository, gateway = service(tmp_path)
    repository.apply_subscription_event(
        event_id="evt_active", event_type="customer.subscription.created",
        update=BillingSubscriptionUpdate(
            actor="key:tenant", customer_id="cus_test", subscription_id="sub_test",
            status=SubscriptionStatus.ACTIVE, current_period_end=None,
            cancel_at_period_end=False, stripe_event_created=100,
        ),
    )
    usage = billing.record_usage(
        "key:tenant", resource_type="job", resource_id="job-1"
    )
    worker = BillingUsageWorker(billing, poll_interval=0.01, retry_delay=0)

    gateway.fail_metering = True
    assert worker.run_once() is True
    gateway.fail_metering = False
    assert worker.run_once() is True
    assert gateway.meter_events[0][2].id == usage.id
    assert repository.usage_summary("key:tenant").reported_units == 1
