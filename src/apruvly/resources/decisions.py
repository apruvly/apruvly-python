"""Decision (approve / reject) endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from apruvly._http import path_escape
from apruvly.models.workflow import DecisionBody

if TYPE_CHECKING:
    from apruvly._http import Requestor


class DecisionsResource:
    """Approve or reject a pending challenge."""

    def __init__(self, requestor: Requestor) -> None:
        self._http = requestor

    def approve(
        self,
        workflow_id: str,
        challenge: str,
        *,
        comment: str | None = None,
    ) -> Any:
        """Approve a pending challenge. Requires ``api:workflow:write``.

        Rate-limited more strictly than the global API limit (10 req/min/IP).
        """
        return self._decide(workflow_id, challenge, approve=True, comment=comment)

    def reject(
        self,
        workflow_id: str,
        challenge: str,
        *,
        comment: str | None = None,
    ) -> Any:
        """Reject a pending challenge. Requires ``api:workflow:write``."""
        return self._decide(workflow_id, challenge, approve=False, comment=comment)

    def _decide(
        self,
        workflow_id: str,
        challenge: str,
        *,
        approve: bool,
        comment: str | None,
    ) -> Any:
        action = "approve" if approve else "reject"
        body = DecisionBody(comment=comment).to_dict() if comment is not None else None
        return self._http.request(
            "PUT",
            f"/api/v1/workflow/{path_escape(workflow_id)}/"
            f"{path_escape(challenge)}/{action}",
            body=body,
            expected_statuses=(200,),
        )
