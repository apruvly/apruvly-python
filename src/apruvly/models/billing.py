"""Billing models (snake_case)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from apruvly.models.common import from_mapping


@dataclass
class SubscriptionInfo:
    status: str | None = None
    billing_period: str | None = None
    trial_ends_at: str | None = None
    current_period_start: str | None = None
    current_period_end: str | None = None
    cancel_at_period_end: bool | None = None
    auto_renew: bool | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> SubscriptionInfo | None:
        return from_mapping(cls, data)


@dataclass
class PlanInfo:
    id: int | None = None
    name: str | None = None
    description: str | None = None
    price: float | None = None
    is_unlimited: bool | None = None
    credit_monthly_allowance: int | None = None
    max_concurrent_workflows: int | None = None
    max_requests_per_minute: int | None = None
    max_requests_per_day: int | None = None
    max_requests_per_cycle: int | None = None
    max_api_keys: int | None = None
    max_approvers: int | None = None
    max_escalations: int | None = None
    max_webhooks: int | None = None
    workflow_timeout_hours: int | None = None
    data_retention_days: int | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> PlanInfo | None:
        return from_mapping(cls, data)


@dataclass
class UsageInfo:
    active_workflows: int | None = None
    workflows_today: int | None = None
    workflows_this_cycle: int | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> UsageInfo | None:
        return from_mapping(cls, data)


@dataclass
class TransactionEntry:
    amount: int | None = None
    balance_after: int | None = None
    reason: str | None = None
    reference_id: str | None = None
    created_at: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TransactionEntry:
        return from_mapping(cls, data)  # type: ignore[return-value]


@dataclass
class BillingInfo:
    """Plan, balance, usage, and recent transactions."""

    subscription: SubscriptionInfo | None = None
    plan: PlanInfo | None = None
    balance: int | None = None
    usage: UsageInfo | None = None
    recent_transactions: list[TransactionEntry] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> BillingInfo:
        txns = data.get("recent_transactions") or []
        return cls(
            subscription=SubscriptionInfo.from_dict(data.get("subscription")),
            plan=PlanInfo.from_dict(data.get("plan")),
            balance=data.get("balance"),
            usage=UsageInfo.from_dict(data.get("usage")),
            recent_transactions=[
                TransactionEntry.from_dict(t)
                for t in txns
                if isinstance(t, Mapping)
            ],
        )
