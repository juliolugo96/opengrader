from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from opengrader.api import create_app
from opengrader.api_models import ApiSettings, api_key_id

pytestmark = pytest.mark.integration


class FakeStripeGateway:
    def __init__(self) -> None:
        self.event = None
        self.meter_events = []

    def create_customer(self, *, actor: str, email: str) -> str:
        assert actor.startswith("key:")
        assert email == "teacher@example.com"
        return "cus_test"

    def create_checkout_session(self, *, actor: str, customer_id: str) -> str:
        assert customer_id == "cus_test"
        return "https://checkout.stripe.test/session"

    def create_portal_session(self, *, customer_id: str) -> str:
        assert customer_id == "cus_test"
        return "https://billing.stripe.test/portal"

    def construct_webhook_event(self, payload: bytes, signature: str, secret: str):
        if signature != "valid" or secret != "whsec_test" or self.event is None:
            raise ValueError("invalid signature")
        return self.event

    def report_usage(self, *, event_name, customer_id, usage) -> None:
        self.meter_events.append((event_name, customer_id, usage))


def api_settings(tmp_path: Path, *, billing_enabled: bool) -> ApiSettings:
    values = dict(
        database_path=tmp_path / "jobs.db",
        output_root=tmp_path / "reports",
        pdf_storage_root=tmp_path / "pdfs",
        api_keys=("valid-key",),
        poll_interval=0.01,
        billing_enabled=billing_enabled,
    )
    if billing_enabled:
        values.update(
            stripe_secret_key="sk_test",
            stripe_webhook_secret="whsec_test",
            stripe_price_id="price_test",
            public_url="https://grader.example",
            stripe_meter_event_name="opengrader_grading_units",
        )
    return ApiSettings(**values)


def job_payload(tmp_path: Path) -> dict[str, object]:
    return {
        "assignment_file": str(tmp_path / "missing-assignment.yaml"),
        "submissions_dir": str(tmp_path / "missing-submissions"),
        "no_docker": True,
    }


def test_local_api_grading_remains_free_when_billing_is_disabled(tmp_path) -> None:
    headers = {"Authorization": "Bearer valid-key"}
    with TestClient(create_app(api_settings(tmp_path, billing_enabled=False))) as client:
        overview = client.get("/v1/billing/overview", headers=headers)
        created = client.post("/v1/jobs", json=job_payload(tmp_path), headers=headers)

    assert overview.status_code == 200
    assert overview.json()["mode"] == "local"
    assert overview.json()["entitled"] is True
    assert created.status_code == 202


def test_hosted_subscription_webhook_unlocks_grading_and_meters_usage(tmp_path) -> None:
    headers = {"Authorization": "Bearer valid-key"}
    gateway = FakeStripeGateway()
    application = create_app(
        api_settings(tmp_path, billing_enabled=True), billing_gateway=gateway
    )
    with TestClient(application) as client:
        blocked = client.post("/v1/jobs", json=job_payload(tmp_path), headers=headers)
        checkout = client.post(
            "/v1/billing/checkout",
            json={"email": "teacher@example.com"},
            headers=headers,
        )
        gateway.event = {
            "id": "evt_active",
            "type": "customer.subscription.created",
            "created": 200,
            "data": {"object": {
                "id": "sub_test", "customer": "cus_test", "status": "active",
                "current_period_end": 1789689600,
                "cancel_at_period_end": False,
                "metadata": {"opengrader_actor": f"key:{api_key_id('valid-key')}"},
                "items": {"data": [{
                    "price": {"id": "price_test"},
                    "current_period_end": 1789689600,
                }]},
            }},
        }
        webhook = client.post(
            "/v1/billing/webhook",
            content=b"raw-body",
            headers={"stripe-signature": "valid"},
        )
        replay = client.post(
            "/v1/billing/webhook",
            content=b"raw-body",
            headers={"stripe-signature": "valid"},
        )
        created = client.post("/v1/jobs", json=job_payload(tmp_path), headers=headers)
        portal = client.post("/v1/billing/portal", headers=headers)

        deadline = time.monotonic() + 1
        while not gateway.meter_events and time.monotonic() < deadline:
            application.state.billing_usage_worker.notify()
            time.sleep(0.01)
        overview = client.get("/v1/billing/overview", headers=headers)

    assert blocked.status_code == 402
    assert checkout.json()["url"].startswith("https://checkout.stripe.test")
    assert webhook.json() == {"received": True, "processed": True}
    assert replay.json() == {"received": True, "processed": False}
    assert created.status_code == 202
    assert portal.json()["url"].endswith("/portal")
    assert overview.json()["status"] == "active"
    assert overview.json()["usage"]["total_units"] == 1
    assert gateway.meter_events[0][0:2] == (
        "opengrader_grading_units", "cus_test"
    )


def test_billing_webhook_rejects_an_invalid_signature(tmp_path) -> None:
    gateway = FakeStripeGateway()
    with TestClient(create_app(
        api_settings(tmp_path, billing_enabled=True), billing_gateway=gateway
    )) as client:
        response = client.post(
            "/v1/billing/webhook",
            content=b"tampered",
            headers={"stripe-signature": "invalid"},
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid Stripe webhook"}
