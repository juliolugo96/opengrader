"""Narrow Stripe SDK adapter used by hosted billing."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

import stripe

from opengrader.billing import BillingUsageEvent


class StripeBillingGateway:
    def __init__(
        self,
        *,
        secret_key: str,
        price_id: str,
        public_url: str,
        client: Any | None = None,
    ) -> None:
        if not secret_key:
            raise ValueError("Stripe secret key is required")
        if not price_id:
            raise ValueError("Stripe price ID is required")
        if not public_url.startswith(("http://", "https://")):
            raise ValueError("public_url must use HTTP or HTTPS")
        self.price_id = price_id
        self.public_url = public_url.rstrip("/")
        self.client = client or stripe.StripeClient(
            secret_key, max_network_retries=2
        )

    def create_customer(self, *, actor: str, email: str) -> str:
        customer = self.client.v1.customers.create(
            {"email": email, "metadata": {"opengrader_actor": actor}},
            {
                "idempotency_key": (
                    "opengrader-customer-"
                    + hashlib.sha256(actor.encode()).hexdigest()
                )
            },
        )
        return _required_attribute(customer, "id")

    def create_checkout_session(self, *, actor: str, customer_id: str) -> str:
        session = self.client.v1.checkout.sessions.create(
            {
                "mode": "subscription",
                "customer": customer_id,
                "client_reference_id": actor,
                "line_items": [{"price": self.price_id}],
                "subscription_data": {
                    "metadata": {"opengrader_actor": actor}
                },
                "success_url": f"{self.public_url}/billing?checkout=success",
                "cancel_url": f"{self.public_url}/billing?checkout=canceled",
            }
        )
        return _required_attribute(session, "url")

    def create_portal_session(self, *, customer_id: str) -> str:
        session = self.client.v1.billing_portal.sessions.create(
            {
                "customer": customer_id,
                "return_url": f"{self.public_url}/billing",
            }
        )
        return _required_attribute(session, "url")

    def construct_webhook_event(
        self, payload: bytes, signature: str, secret: str
    ) -> Mapping[str, Any]:
        event = stripe.Webhook.construct_event(payload, signature, secret)
        if not isinstance(event, Mapping):
            raise ValueError("Stripe webhook did not produce an event object")
        return event

    def report_usage(
        self,
        *,
        event_name: str,
        customer_id: str,
        usage: BillingUsageEvent,
    ) -> None:
        self.client.v1.billing.meter_events.create(
            {
                "event_name": event_name,
                "identifier": usage.id,
                "payload": {
                    "stripe_customer_id": customer_id,
                    "value": str(usage.quantity),
                    "resource_type": usage.resource_type,
                },
            }
        )


def _required_attribute(value: object, attribute: str) -> str:
    candidate = getattr(value, attribute, None)
    if not isinstance(candidate, str) or not candidate:
        raise RuntimeError(f"Stripe response did not include {attribute}")
    return candidate
