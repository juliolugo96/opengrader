from types import SimpleNamespace

import pytest

from opengrader.billing import BillingUsageEvent, UsageDeliveryStatus
from opengrader.stripe_gateway import StripeBillingGateway

pytestmark = pytest.mark.unit


class RecordingService:
    def __init__(self, response) -> None:
        self.response = response
        self.calls = []

    def create(self, params, options=None):
        self.calls.append((params, options))
        return self.response


def fake_client():
    customers = RecordingService(SimpleNamespace(id="cus_test"))
    checkout = RecordingService(SimpleNamespace(url="https://checkout.stripe.test/cs"))
    portal = RecordingService(SimpleNamespace(url="https://billing.stripe.test/session"))
    meters = RecordingService(SimpleNamespace())
    client = SimpleNamespace(v1=SimpleNamespace(
        customers=customers,
        checkout=SimpleNamespace(sessions=checkout),
        billing_portal=SimpleNamespace(sessions=portal),
        billing=SimpleNamespace(meter_events=meters),
    ))
    return client, customers, checkout, portal, meters


def test_stripe_gateway_creates_customer_checkout_and_portal_with_server_owned_fields() -> None:
    client, customers, checkout, portal, _ = fake_client()
    gateway = StripeBillingGateway(
        secret_key="sk_test", price_id="price_pro",
        public_url="https://grader.example/", client=client,
    )

    assert gateway.create_customer(
        actor="key:tenant", email="teacher@example.com"
    ) == "cus_test"
    assert gateway.create_checkout_session(
        actor="key:tenant", customer_id="cus_test"
    ).startswith("https://checkout.stripe.test")
    assert gateway.create_portal_session(customer_id="cus_test").endswith("/session")

    assert customers.calls[0][0]["metadata"] == {"opengrader_actor": "key:tenant"}
    checkout_params = checkout.calls[0][0]
    assert checkout_params["mode"] == "subscription"
    assert checkout_params["line_items"] == [{"price": "price_pro"}]
    assert checkout_params["subscription_data"]["metadata"] == {
        "opengrader_actor": "key:tenant"
    }
    assert checkout_params["success_url"] == (
        "https://grader.example/billing?checkout=success"
    )
    assert portal.calls[0][0]["return_url"] == "https://grader.example/billing"


def test_stripe_gateway_reports_idempotent_meter_event() -> None:
    client, _, _, _, meters = fake_client()
    gateway = StripeBillingGateway(
        secret_key="sk_test", price_id="price_pro",
        public_url="https://grader.example", client=client,
    )
    usage = BillingUsageEvent(
        id="usage-123", actor="key:tenant", resource_type="job",
        resource_id="job-123", quantity=3, status=UsageDeliveryStatus.PENDING,
        attempts=0, last_error=None, created_at="2026-08-18T12:00:00Z",
        customer_id="cus_test",
    )

    gateway.report_usage(
        event_name="opengrader_grading_units",
        customer_id="cus_test",
        usage=usage,
    )

    assert meters.calls == [({
        "event_name": "opengrader_grading_units",
        "identifier": "usage-123",
        "payload": {
            "stripe_customer_id": "cus_test",
            "value": "3",
            "resource_type": "job",
        },
    }, None)]
