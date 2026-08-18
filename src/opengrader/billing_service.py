"""Hosted billing orchestration and durable Stripe usage delivery."""

from __future__ import annotations

import threading
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Protocol

from opengrader.billing import (
    BillingMode,
    BillingOverview,
    BillingSessionResponse,
    BillingSubscriptionUpdate,
    BillingUsageEvent,
    BillingUsageSummary,
)
from opengrader.billing_contract import (
    SubscriptionStatus,
    is_entitled,
    normalize_subscription_status,
)
from opengrader.billing_repository import BillingRepository


class BillingRequired(RuntimeError):
    pass


class BillingNotConfigured(RuntimeError):
    pass


class BillingWebhookError(ValueError):
    pass


class BillingGateway(Protocol):
    def create_customer(self, *, actor: str, email: str) -> str: ...

    def create_checkout_session(self, *, actor: str, customer_id: str) -> str: ...

    def create_portal_session(self, *, customer_id: str) -> str: ...

    def construct_webhook_event(
        self, payload: bytes, signature: str, secret: str
    ) -> Mapping[str, Any]: ...

    def report_usage(
        self,
        *,
        event_name: str,
        customer_id: str,
        usage: BillingUsageEvent,
    ) -> None: ...


class BillingService:
    def __init__(
        self,
        repository: BillingRepository,
        *,
        enabled: bool,
        gateway: BillingGateway | None,
        webhook_secret: str | None,
        price_id: str | None,
        meter_event_name: str,
    ) -> None:
        if enabled and (gateway is None or not webhook_secret or not price_id):
            raise BillingNotConfigured(
                "Hosted billing requires a Stripe gateway and webhook secret"
            )
        if not meter_event_name or len(meter_event_name) > 100:
            raise ValueError("meter_event_name must contain between 1 and 100 characters")
        self.repository = repository
        self.enabled = enabled
        self.gateway = gateway
        self.webhook_secret = webhook_secret
        self.price_id = price_id
        self.meter_event_name = meter_event_name

    def overview(self, actor: str) -> BillingOverview:
        if not self.enabled:
            return BillingOverview(
                mode=BillingMode.LOCAL,
                status=SubscriptionStatus.NONE,
                entitled=True,
                customer_configured=False,
                subscription_configured=False,
                current_period_end=None,
                cancel_at_period_end=False,
                usage=BillingUsageSummary(),
            )
        account = self.repository.ensure_account(actor)
        return BillingOverview(
            mode=BillingMode.HOSTED,
            status=account.status,
            entitled=is_entitled(account.status),
            customer_configured=account.customer_id is not None,
            subscription_configured=account.subscription_id is not None,
            current_period_end=account.current_period_end,
            cancel_at_period_end=account.cancel_at_period_end,
            usage=self.repository.usage_summary(actor),
        )

    def require_entitlement(self, actor: str) -> None:
        if not self.enabled:
            return
        account = self.repository.ensure_account(actor)
        if not is_entitled(account.status):
            raise BillingRequired(
                "An active hosted subscription is required to create grading work"
            )

    def create_checkout(self, actor: str, *, email: str) -> BillingSessionResponse:
        gateway = self._configured_gateway()
        account = self.repository.ensure_account(actor)
        if account.status not in {
            SubscriptionStatus.NONE,
            SubscriptionStatus.CANCELED,
            SubscriptionStatus.INCOMPLETE_EXPIRED,
        }:
            raise BillingRequired(
                "Manage the existing subscription instead of starting another checkout"
            )
        customer_id = account.customer_id
        if customer_id is None:
            customer_id = gateway.create_customer(actor=actor, email=email)
            self.repository.bind_customer(actor, customer_id)
        return BillingSessionResponse(
            url=gateway.create_checkout_session(actor=actor, customer_id=customer_id)
        )

    def create_portal(self, actor: str) -> BillingSessionResponse:
        gateway = self._configured_gateway()
        account = self.repository.get_account(actor)
        if account is None or account.customer_id is None:
            raise BillingRequired("Start a subscription before opening billing management")
        return BillingSessionResponse(
            url=gateway.create_portal_session(customer_id=account.customer_id)
        )

    def handle_webhook(self, payload: bytes, signature: str) -> bool:
        gateway = self._configured_gateway()
        try:
            if self.webhook_secret is None:
                raise BillingNotConfigured("Stripe webhook secret is missing")
            event = gateway.construct_webhook_event(
                payload, signature, self.webhook_secret
            )
            event_id = _required_string(event, "id")
            event_type = _required_string(event, "type")
            event_created = _nonnegative_int(event.get("created", 0), "created")
            data = _mapping(event.get("data"), "data")
            stripe_object = _mapping(data.get("object"), "data.object")
        except BillingWebhookError:
            raise
        except Exception as exc:
            raise BillingWebhookError("Invalid Stripe webhook") from exc

        if event_type == "checkout.session.completed":
            actor = _required_string(stripe_object, "client_reference_id")
            customer_id = _stripe_id(stripe_object.get("customer"), "customer")
            subscription_id = _optional_stripe_id(stripe_object.get("subscription"))
            return self.repository.apply_checkout_event(
                event_id=event_id,
                event_type=event_type,
                actor=actor,
                customer_id=customer_id,
                subscription_id=subscription_id,
            )

        if event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        }:
            customer_id = _stripe_id(stripe_object.get("customer"), "customer")
            subscription_id = _required_string(stripe_object, "id")
            metadata = _mapping(stripe_object.get("metadata", {}), "metadata")
            actor_value = metadata.get("opengrader_actor")
            actor = (
                actor_value
                if isinstance(actor_value, str) and actor_value
                else self.repository.actor_for_customer(customer_id)
            )
            if actor is None:
                return self.repository.record_webhook_event(
                    event_id=event_id, event_type=event_type
                )
            if not _subscription_has_price(stripe_object, self.price_id):
                return self.repository.record_webhook_event(
                    event_id=event_id, event_type=event_type
                )
            timestamp = _subscription_period_end(stripe_object)
            period_end = (
                datetime.fromtimestamp(
                    _nonnegative_int(timestamp, "current_period_end"), tz=UTC
                )
                if timestamp is not None
                else None
            )
            status = (
                SubscriptionStatus.CANCELED
                if event_type == "customer.subscription.deleted"
                else normalize_subscription_status(stripe_object.get("status"))
            )
            update = BillingSubscriptionUpdate(
                actor=actor,
                customer_id=customer_id,
                subscription_id=subscription_id,
                status=status,
                current_period_end=period_end,
                cancel_at_period_end=bool(
                    stripe_object.get("cancel_at_period_end", False)
                ),
                stripe_event_created=event_created,
            )
            return self.repository.apply_subscription_event(
                event_id=event_id, event_type=event_type, update=update
            )

        return self.repository.record_webhook_event(
            event_id=event_id, event_type=event_type
        )

    def record_usage(
        self,
        actor: str,
        *,
        resource_type: str,
        resource_id: str,
        quantity: int = 1,
    ) -> BillingUsageEvent | None:
        if not self.enabled:
            return None
        return self.repository.record_usage(
            actor=actor,
            resource_type=resource_type,
            resource_id=resource_id,
            quantity=quantity,
        )

    def report_next_usage(self, *, retry_delay: float) -> bool:
        gateway = self._configured_gateway()
        usage = self.repository.next_reportable_usage()
        if usage is None:
            return False
        if usage.customer_id is None:
            raise RuntimeError("reportable usage is missing a Stripe customer")
        try:
            gateway.report_usage(
                event_name=self.meter_event_name,
                customer_id=usage.customer_id,
                usage=usage,
            )
        except Exception as exc:
            self.repository.mark_usage_failed(
                usage.id,
                f"{type(exc).__name__}: {exc}",
                retry_after_seconds=retry_delay,
            )
        else:
            self.repository.mark_usage_reported(usage.id)
        return True

    def _configured_gateway(self) -> BillingGateway:
        if not self.enabled or self.gateway is None:
            raise BillingNotConfigured("Stripe billing is disabled in this deployment")
        return self.gateway


class BillingUsageWorker:
    def __init__(
        self,
        service: BillingService,
        *,
        poll_interval: float = 5,
        retry_delay: float = 30,
    ) -> None:
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive")
        if retry_delay < 0:
            raise ValueError("retry_delay cannot be negative")
        self.service = service
        self.poll_interval = poll_interval
        self.retry_delay = retry_delay
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self.service.enabled:
            return
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="opengrader-billing-usage-worker",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 5) -> None:
        self._stop_event.set()
        self._wake_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def notify(self) -> None:
        self._wake_event.set()

    def run_once(self) -> bool:
        if not self.service.enabled:
            return False
        return self.service.report_next_usage(retry_delay=self.retry_delay)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            processed = self.run_once()
            if not processed:
                self._wake_event.wait(self.poll_interval)
                self._wake_event.clear()


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BillingWebhookError(f"Stripe webhook {field} must be an object")
    return value


def _required_string(value: Mapping[str, Any], field: str) -> str:
    candidate = value.get(field)
    if not isinstance(candidate, str) or not candidate:
        raise BillingWebhookError(f"Stripe webhook {field} is missing")
    return candidate


def _stripe_id(value: object, field: str) -> str:
    candidate = _optional_stripe_id(value)
    if candidate is None:
        raise BillingWebhookError(f"Stripe webhook {field} is missing")
    return candidate


def _optional_stripe_id(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, Mapping):
        identifier = value.get("id")
        if isinstance(identifier, str) and identifier:
            return identifier
    return None


def _nonnegative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BillingWebhookError(f"Stripe webhook {field} must be a timestamp")
    return value


def _subscription_has_price(
    subscription: Mapping[str, Any], price_id: str | None
) -> bool:
    if price_id is None:
        return False
    items = subscription.get("items")
    if not isinstance(items, Mapping):
        return False
    data = items.get("data")
    if not isinstance(data, list):
        return False
    for item in data:
        if not isinstance(item, Mapping):
            continue
        price = item.get("price")
        if price == price_id:
            return True
        if isinstance(price, Mapping) and price.get("id") == price_id:
            return True
        plan = item.get("plan")
        if isinstance(plan, Mapping) and plan.get("id") == price_id:
            return True
    return False


def _subscription_period_end(subscription: Mapping[str, Any]) -> object:
    direct = subscription.get("current_period_end")
    if direct is not None:
        return direct
    items = subscription.get("items")
    if not isinstance(items, Mapping):
        return None
    data = items.get("data")
    if not isinstance(data, list):
        return None
    timestamps = [
        item.get("current_period_end")
        for item in data
        if isinstance(item, Mapping)
        and isinstance(item.get("current_period_end"), int)
        and not isinstance(item.get("current_period_end"), bool)
    ]
    return max(timestamps) if timestamps else None
