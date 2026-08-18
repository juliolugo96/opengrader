"""Pure hosted-billing entitlement and usage invariants."""

from __future__ import annotations

from enum import StrEnum


class SubscriptionStatus(StrEnum):
    NONE = "none"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    PAUSED = "paused"


def normalize_subscription_status(value: object) -> SubscriptionStatus:
    try:
        return SubscriptionStatus(value)
    except (TypeError, ValueError):
        return SubscriptionStatus.NONE


def is_entitled(status: SubscriptionStatus) -> bool:
    return status in {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING}


def validate_usage_quantity(quantity: object) -> int:
    if (
        isinstance(quantity, bool)
        or not isinstance(quantity, int)
        or not 1 <= quantity <= 10_000
    ):
        raise ValueError("usage quantity must be an integer between 1 and 10000")
    return quantity

