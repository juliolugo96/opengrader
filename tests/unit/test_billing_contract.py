from datetime import UTC, datetime

import pytest

from opengrader.billing_contract import (
    SubscriptionStatus,
    is_entitled,
    normalize_subscription_status,
    validate_usage_quantity,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (SubscriptionStatus.ACTIVE, True),
        (SubscriptionStatus.TRIALING, True),
        (SubscriptionStatus.NONE, False),
        (SubscriptionStatus.INCOMPLETE, False),
        (SubscriptionStatus.PAST_DUE, False),
        (SubscriptionStatus.CANCELED, False),
        (SubscriptionStatus.UNPAID, False),
        (SubscriptionStatus.PAUSED, False),
    ],
)
def test_entitlements_are_explicit_and_fail_closed(status, expected: bool) -> None:
    assert is_entitled(status) is expected


def test_unknown_stripe_subscription_status_fails_closed() -> None:
    assert normalize_subscription_status("active") is SubscriptionStatus.ACTIVE
    assert normalize_subscription_status("future_status") is SubscriptionStatus.NONE
    assert normalize_subscription_status(None) is SubscriptionStatus.NONE


@pytest.mark.parametrize("quantity", [1, 2, 10_000])
def test_usage_quantities_accept_positive_bounded_integers(quantity: int) -> None:
    assert validate_usage_quantity(quantity) == quantity


@pytest.mark.parametrize("quantity", [0, -1, 10_001, True, 1.5])
def test_usage_quantities_reject_invalid_values(quantity) -> None:
    with pytest.raises(
        ValueError,
        match="^usage quantity must be an integer between 1 and 10000$",
    ):
        validate_usage_quantity(quantity)
