from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pytest_bdd import given, scenarios, then, when

from opengrader.api import create_app
from opengrader.api_models import ApiSettings, api_key_id

pytestmark = pytest.mark.e2e
scenarios("../features/billing.feature")


class BillingGateway:
    def __init__(self) -> None:
        self.event = None
        self.meter_events = []

    def create_customer(self, *, actor: str, email: str) -> str:
        return "cus_bdd"

    def create_checkout_session(self, *, actor: str, customer_id: str) -> str:
        return "https://checkout.stripe.test/bdd"

    def create_portal_session(self, *, customer_id: str) -> str:
        return "https://billing.stripe.test/bdd"

    def construct_webhook_event(self, payload: bytes, signature: str, secret: str):
        if signature != "signed" or secret != "whsec_bdd" or self.event is None:
            raise ValueError("invalid signature")
        return self.event

    def report_usage(self, *, event_name, customer_id, usage) -> None:
        self.meter_events.append((event_name, customer_id, usage))


@pytest.fixture
def billing_world(tmp_path: Path):
    gateway = BillingGateway()
    settings = ApiSettings(
        database_path=tmp_path / "jobs.db",
        output_root=tmp_path / "reports",
        pdf_storage_root=tmp_path / "pdfs",
        api_keys=("bdd-key",),
        poll_interval=0.01,
        billing_enabled=True,
        stripe_secret_key="sk_test_bdd",
        stripe_webhook_secret="whsec_bdd",
        stripe_price_id="price_bdd",
        public_url="https://grader.example",
    )
    application = create_app(settings, billing_gateway=gateway)
    context = TestClient(application)
    client = context.__enter__()
    world = {
        "application": application,
        "client": client,
        "context": context,
        "gateway": gateway,
        "headers": {"Authorization": "Bearer bdd-key"},
        "tmp_path": tmp_path,
    }
    yield world
    context.__exit__(None, None, None)


@given("a hosted OpenGrader billing API")
def hosted_billing_api(billing_world):
    assert billing_world["client"].get("/health").status_code == 200


@when("I try to create grading work without a subscription")
def create_without_subscription(billing_world):
    billing_world["blocked"] = billing_world["client"].post(
        "/v1/jobs",
        json={
            "assignment_file": str(billing_world["tmp_path"] / "assignment.yaml"),
            "submissions_dir": str(billing_world["tmp_path"] / "submissions"),
            "no_docker": True,
        },
        headers=billing_world["headers"],
    )


@then("hosted grading requires payment")
def payment_required(billing_world):
    assert billing_world["blocked"].status_code == 402


@when("Stripe sends a signed active subscription event")
def active_subscription_event(billing_world):
    billing_world["gateway"].event = {
        "id": "evt_bdd",
        "type": "customer.subscription.created",
        "created": 100,
        "data": {"object": {
            "id": "sub_bdd",
            "customer": "cus_bdd",
            "status": "active",
            "cancel_at_period_end": False,
            "metadata": {"opengrader_actor": f"key:{api_key_id('bdd-key')}"},
            "items": {"data": [{
                "price": {"id": "price_bdd"},
                "current_period_end": 1789689600,
            }]},
        }},
    }
    billing_world["webhook"] = billing_world["client"].post(
        "/v1/billing/webhook",
        content=b"signed-raw-body",
        headers={"stripe-signature": "signed"},
    )


@then("the hosted tenant becomes entitled")
def tenant_entitled(billing_world):
    assert billing_world["webhook"].json()["processed"] is True
    overview = billing_world["client"].get(
        "/v1/billing/overview", headers=billing_world["headers"]
    )
    assert overview.json()["entitled"] is True


@when("I create an entitled grading job")
def create_entitled_job(billing_world):
    billing_world["created"] = billing_world["client"].post(
        "/v1/jobs",
        json={
            "assignment_file": str(billing_world["tmp_path"] / "assignment.yaml"),
            "submissions_dir": str(billing_world["tmp_path"] / "submissions"),
            "no_docker": True,
        },
        headers=billing_world["headers"],
    )


@then("one durable usage unit is reported to Stripe")
def usage_reported(billing_world):
    assert billing_world["created"].status_code == 202
    deadline = time.monotonic() + 1
    while not billing_world["gateway"].meter_events and time.monotonic() < deadline:
        billing_world["application"].state.billing_usage_worker.notify()
        time.sleep(0.01)
    assert len(billing_world["gateway"].meter_events) == 1
    assert billing_world["gateway"].meter_events[0][2].quantity == 1


@then("replaying the Stripe event does not apply it twice")
def webhook_replay(billing_world):
    replay = billing_world["client"].post(
        "/v1/billing/webhook",
        content=b"signed-raw-body",
        headers={"stripe-signature": "signed"},
    )
    assert replay.json() == {"received": True, "processed": False}
