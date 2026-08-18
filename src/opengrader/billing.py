"""Serializable contracts for optional hosted billing."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from opengrader.billing_contract import SubscriptionStatus


class BillingMode(StrEnum):
    LOCAL = "local"
    HOSTED = "hosted"


class UsageDeliveryStatus(StrEnum):
    PENDING = "pending"
    REPORTED = "reported"
    FAILED = "failed"


class BillingAccount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor: str
    customer_id: str | None = None
    subscription_id: str | None = None
    status: SubscriptionStatus = SubscriptionStatus.NONE
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    stripe_event_created: int = 0
    created_at: datetime
    updated_at: datetime


class BillingSubscriptionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor: str
    customer_id: str
    subscription_id: str
    status: SubscriptionStatus
    current_period_end: datetime | None
    cancel_at_period_end: bool
    stripe_event_created: int = Field(ge=0)


class BillingUsageEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    actor: str
    resource_type: str
    resource_id: str
    quantity: int
    status: UsageDeliveryStatus
    attempts: int
    last_error: str | None
    created_at: datetime
    reported_at: datetime | None = None
    customer_id: str | None = None


class BillingUsageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_units: int = 0
    reported_units: int = 0
    pending_units: int = 0


class BillingOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: BillingMode
    status: SubscriptionStatus
    entitled: bool
    customer_configured: bool
    subscription_configured: bool
    current_period_end: datetime | None
    cancel_at_period_end: bool
    usage: BillingUsageSummary


class BillingCheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(
        min_length=3,
        max_length=254,
        pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
    )


class BillingSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(pattern=r"^https://")


class BillingWebhookResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    received: bool = True
    processed: bool

