"""Billing endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from apruvly.models.billing import BillingInfo

if TYPE_CHECKING:
    from apruvly._http import Requestor


class BillingResource:
    """Plan, balance, and usage."""

    def __init__(self, requestor: Requestor) -> None:
        self._http = requestor

    def get(self) -> BillingInfo:
        """Fetch billing info. Requires ``api:settings:read``."""
        data = self._http.request(
            "GET",
            "/api/v1/billing",
            expected_statuses=(200,),
        )
        return BillingInfo.from_dict(data or {})
