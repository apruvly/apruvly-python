"""Exception hierarchy for the Apruvly API client."""

from __future__ import annotations

from typing import Any


class ApruvlyError(Exception):
    """Base error for all Apruvly client failures.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code when the error came from an API response.
        error_code: Machine-readable ``errorCode`` from the API, if present.
        data: Raw ``data`` object from the API error envelope, if present.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        data: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.data = data

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code is not None:
            parts.append(f"status={self.status_code}")
        if self.error_code:
            parts.append(f"error_code={self.error_code}")
        return " | ".join(parts)


class AuthError(ApruvlyError):
    """Raised on HTTP 401 — missing or invalid API key."""


class ForbiddenError(ApruvlyError):
    """Raised on HTTP 403 — authenticated but missing required scope."""


class NotFoundError(ApruvlyError):
    """Raised on HTTP 404 — resource not found."""


class ValidationError(ApruvlyError):
    """Raised on HTTP 400 / 422 — invalid request or missing integration."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        data: Any = None,
        field: str | None = None,
        parameter: str | None = None,
        integration: str | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            error_code=error_code,
            data=data,
        )
        self.field = field
        self.parameter = parameter
        self.integration = integration


class PaymentRequiredError(ApruvlyError):
    """Raised on HTTP 402 — insufficient credits or plan feature gate."""


class ConflictError(ApruvlyError):
    """Raised on HTTP 409 — conflict (e.g. duplicate external_id, directory disabled)."""


class NotAcceptableError(ApruvlyError):
    """Raised on HTTP 406 — workflow already closed (cancel / decide)."""


class QuotaExceededError(ApruvlyError):
    """Raised on HTTP 429 — rate limit or plan quota exceeded.

    Attributes:
        quota_type: Quota dimension (e.g. ``requests_per_minute``).
        limit: Configured limit for that quota, when provided.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = 429,
        error_code: str | None = None,
        data: Any = None,
        quota_type: str | None = None,
        limit: int | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            error_code=error_code,
            data=data,
        )
        self.quota_type = quota_type
        self.limit = limit


class APIError(ApruvlyError):
    """Raised for unexpected HTTP responses or transport failures."""
