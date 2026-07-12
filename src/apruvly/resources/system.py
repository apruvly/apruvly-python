"""System endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apruvly._http import Requestor


class SystemResource:
    """System / health operations."""

    def __init__(self, requestor: Requestor) -> None:
        self._http = requestor

    def health(self) -> Any:
        """Check API liveness.

        Any authenticated API key works; no scope is required.

        Returns:
            Unwrapped ``data`` from the health envelope (shape may evolve).
        """
        return self._http.request("GET", "/api/v1/health", expected_statuses=(200,))
