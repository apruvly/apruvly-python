"""Workflow endpoints."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from apruvly._http import path_escape
from apruvly.models.workflow import (
    WorkflowConfig,
    WorkflowCreated,
    WorkflowState,
    WorkflowStatus,
    as_workflow_payload,
)

if TYPE_CHECKING:
    from apruvly._http import Requestor


class WorkflowsResource:
    """Create, inspect, search, and cancel workflows."""

    def __init__(self, requestor: Requestor) -> None:
        self._http = requestor

    def create(
        self, config: WorkflowConfig | Mapping[str, Any]
    ) -> WorkflowCreated:
        """Create a workflow (debits credits). Requires ``api:workflow:write``.

        Args:
            config: Workflow definition as :class:`~apruvly.models.WorkflowConfig`
                or a plain dict matching the OpenAPI ``WorkflowConfig`` schema.

        Returns:
            :class:`~apruvly.models.WorkflowCreated` with the new workflow id.

        Raises:
            apruvly.ValidationError: Invalid configuration.
            apruvly.PaymentRequiredError: Insufficient credits.
            apruvly.QuotaExceededError: Rate / plan quota exceeded.
        """
        data = self._http.request(
            "POST",
            "/api/v1/workflow",
            body=as_workflow_payload(config),
            expected_statuses=(202,),
        )
        return WorkflowCreated.from_dict(data or {})

    def validate(self, config: WorkflowConfig | Mapping[str, Any]) -> Any:
        """Validate a workflow without persisting or charging credits.

        Requires ``api:workflow:write``.
        """
        return self._http.request(
            "POST",
            "/api/v1/workflow/validate",
            body=as_workflow_payload(config),
            expected_statuses=(200,),
        )

    def get(self, workflow_id: str) -> WorkflowStatus:
        """Get full workflow status by UUID. Requires ``api:workflow:read``."""
        data = self._http.request(
            "GET",
            f"/api/v1/workflow/{path_escape(workflow_id)}",
            expected_statuses=(200,),
        )
        return WorkflowStatus.from_dict(data or {})

    def get_by_external_id(self, external_id: str) -> WorkflowStatus:
        """Get workflow status by correlation id (Growth+). Requires ``api:workflow:read``."""
        data = self._http.request(
            "GET",
            f"/api/v1/workflow/external/{path_escape(external_id)}",
            expected_statuses=(200,),
        )
        return WorkflowStatus.from_dict(data or {})

    def cancel(self, workflow_id: str) -> dict[str, Any]:
        """Cancel a pending workflow by UUID. Requires ``api:workflow:cancel``."""
        data = self._http.request(
            "DELETE",
            f"/api/v1/workflow/{path_escape(workflow_id)}",
            expected_statuses=(200,),
        )
        return dict(data or {})

    def cancel_by_external_id(self, external_id: str) -> dict[str, Any]:
        """Cancel by external id (Growth+). Requires ``api:workflow:cancel``."""
        data = self._http.request(
            "DELETE",
            f"/api/v1/workflow/external/{path_escape(external_id)}",
            expected_statuses=(200,),
        )
        return dict(data or {})

    def search(
        self,
        *,
        query: str | None = None,
        status: str | None = None,
        stage: str | None = None,
        step: str | None = None,
        tags: str | list[str] | None = None,
        external_id: str | None = None,
        from_: str | None = None,
        to: str | None = None,
        limit: int | None = None,
    ) -> list[WorkflowState]:
        """Search workflows. Requires ``api:workflow:list``.

        Args:
            query: Full-text search on title / description.
            status: ``pending``, ``approved``, ``rejected``, ``canceled``,
                ``expired``, ``error`` (``active`` is an alias for ``pending``).
            stage: Filter by current step id.
            step: Alias of ``stage``.
            tags: Comma-separated string or list of tags.
            external_id: Growth+ only.
            from_: Created-at lower bound (RFC3339).
            to: Created-at upper bound (RFC3339).
            limit: Max rows (default 50, max 500).
        """
        tag_value: str | None
        if isinstance(tags, list):
            tag_value = ",".join(tags)
        else:
            tag_value = tags

        data = self._http.request(
            "GET",
            "/api/v1/workflows/search",
            params={
                "query": query,
                "status": status,
                "stage": stage,
                "step": step,
                "tags": tag_value,
                "external_id": external_id,
                "from": from_,
                "to": to,
                "limit": limit,
            },
            expected_statuses=(200,),
        )
        rows = data or []
        return [
            WorkflowState.from_dict(row) for row in rows if isinstance(row, Mapping)
        ]

    def recent(self) -> list[WorkflowState]:
        """Return the 10 most recent workflows. Requires ``api:workflow:list``."""
        data = self._http.request(
            "GET",
            "/api/v1/workflows/recent",
            expected_statuses=(200,),
        )
        rows = data or []
        return [
            WorkflowState.from_dict(row) for row in rows if isinstance(row, Mapping)
        ]
