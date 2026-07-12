"""Client-side throttle and retry settings (conservative defaults)."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# Statuses that usually mean "try again" without implying the write committed.
DEFAULT_RETRY_STATUSES: frozenset[int] = frozenset({429, 502, 503, 504})

# Methods considered safe to retry after transport drops (no clear HTTP reply).
# POST is excluded by default to avoid duplicate workflow creates.
DEFAULT_RETRY_TRANSPORT_METHODS: frozenset[str] = frozenset(
    {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"}
)


@dataclass(frozen=True)
class RetryConfig:
    """Throttle + retry policy for the HTTP transport.

    Defaults are intentionally conservative to protect the Apruvly API and
    avoid amplifying load during incidents.

    Attributes:
        min_interval: Minimum seconds between the *start* of consecutive
            requests from this client (client-side throttle). ``0`` disables.
        max_retries: Extra attempts after the first try (``2`` ⇒ up to 3 total).
        backoff_factor: Base delay in seconds for exponential backoff
            (``factor * 2**attempt``).
        backoff_max: Cap on computed backoff (and on ``Retry-After`` waits).
        jitter: When True, sleep a random fraction of the computed delay
            (full jitter) to desynchronize clients.
        retry_statuses: HTTP statuses that trigger a retry.
        retry_transport_methods: Methods retried after connection / TLS /
            timeout-style :class:`urllib.error.URLError` failures. ``POST`` is
            omitted by default.
        retry_on_timeout: Retry when the failure looks like a socket timeout
            (still respects ``retry_transport_methods``).
    """

    min_interval: float = 0.2
    max_retries: int = 2
    backoff_factor: float = 1.0
    backoff_max: float = 30.0
    jitter: bool = True
    retry_statuses: frozenset[int] = DEFAULT_RETRY_STATUSES
    retry_transport_methods: frozenset[str] = DEFAULT_RETRY_TRANSPORT_METHODS
    retry_on_timeout: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "retry_statuses", frozenset(self.retry_statuses))
        object.__setattr__(
            self,
            "retry_transport_methods",
            frozenset(m.upper() for m in self.retry_transport_methods),
        )
        if self.min_interval < 0:
            raise ValueError("min_interval must be >= 0")
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.backoff_factor < 0:
            raise ValueError("backoff_factor must be >= 0")
        if self.backoff_max < 0:
            raise ValueError("backoff_max must be >= 0")

    @classmethod
    def conservative(cls) -> RetryConfig:
        """Library default policy (same as constructing ``RetryConfig()``)."""
        return cls()

    @classmethod
    def disabled(cls) -> RetryConfig:
        """No throttle and no retries (useful in unit tests)."""
        return cls(min_interval=0.0, max_retries=0, jitter=False)

    @classmethod
    def from_env(cls, base: RetryConfig | None = None) -> RetryConfig:
        """Build config from ``APRUVLY_*`` environment overrides.

        Recognized variables:

        - ``APRUVLY_MIN_INTERVAL``
        - ``APRUVLY_MAX_RETRIES``
        - ``APRUVLY_BACKOFF_FACTOR``
        - ``APRUVLY_BACKOFF_MAX``
        - ``APRUVLY_RETRY_JITTER`` (``1``/``0``, ``true``/``false``)
        """
        cfg = base or cls()
        return replace(
            cfg,
            min_interval=_env_float("APRUVLY_MIN_INTERVAL", cfg.min_interval),
            max_retries=_env_int("APRUVLY_MAX_RETRIES", cfg.max_retries),
            backoff_factor=_env_float("APRUVLY_BACKOFF_FACTOR", cfg.backoff_factor),
            backoff_max=_env_float("APRUVLY_BACKOFF_MAX", cfg.backoff_max),
            jitter=_env_bool("APRUVLY_RETRY_JITTER", cfg.jitter),
        )
