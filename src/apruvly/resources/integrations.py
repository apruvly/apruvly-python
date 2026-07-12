"""Integration endpoints."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from apruvly._http import path_escape
from apruvly.models.integration import (
    IntegrationConfig,
    IntegrationStatus,
    as_integration_payload,
)

if TYPE_CHECKING:
    from apruvly._http import Requestor


class IntegrationsResource:
    """Notification channel credentials."""

    def __init__(self, requestor: Requestor) -> None:
        self._http = requestor

    def list(self) -> list[IntegrationStatus]:
        """List all integration statuses. Requires ``api:settings:read``."""
        data = self._http.request(
            "GET",
            "/api/v1/integrations",
            expected_statuses=(200,),
        )
        rows = data or []
        return [
            IntegrationStatus.from_dict(row)
            for row in rows
            if isinstance(row, Mapping)
        ]

    def get(self, integration: str) -> IntegrationStatus:
        """Get one integration. Requires ``api:settings:read``."""
        data = self._http.request(
            "GET",
            f"/api/v1/integrations/{path_escape(integration)}",
            expected_statuses=(200,),
        )
        return IntegrationStatus.from_dict(data or {})

    def upsert(self, integration: str, config: IntegrationConfig) -> None:
        """Create or replace integration credentials. Requires ``api:settings:write``.

        Returns:
            ``None`` (HTTP 204).
        """
        self._http.request(
            "PUT",
            f"/api/v1/integrations/{path_escape(integration)}",
            body=as_integration_payload(config),
            expected_statuses=(204,),
        )

    def delete(self, integration: str) -> None:
        """Remove an integration. Requires ``api:settings:write``."""
        self._http.request(
            "DELETE",
            f"/api/v1/integrations/{path_escape(integration)}",
            expected_statuses=(204,),
        )
