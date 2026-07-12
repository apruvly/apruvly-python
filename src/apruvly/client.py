"""Top-level Apruvly API client."""

from __future__ import annotations

import os
from typing import Any
from urllib.request import OpenerDirector

from apruvly._http import (
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    Requestor,
)
from apruvly._retry import RetryConfig
from apruvly.resources.billing import BillingResource
from apruvly.resources.decisions import DecisionsResource
from apruvly.resources.directory import DirectoryResource
from apruvly.resources.integrations import IntegrationsResource
from apruvly.resources.system import SystemResource
from apruvly.resources.workflows import WorkflowsResource


class Client:
    """Synchronous Apruvly REST API client (stdlib only).

    Example:
        >>> from apruvly import Client, RetryConfig
        >>> client = Client(api_key="wf-...")
        >>> # Point at a local / staging API:
        >>> client = Client(api_key="wf-...", base_url="http://localhost:1509")
        >>> # Or set APRUVLY_BASE_URL / APRUVLY_API_KEY in the environment.
        >>> client = Client()
        >>> # Tighten or relax throttle / retries:
        >>> client = Client(retry=RetryConfig(min_interval=0.5, max_retries=3))
        >>> client.health()

    Attributes:
        workflows: Create, validate, get, cancel, search workflows.
        decisions: Approve or reject pending challenges.
        billing: Plan, balance, and usage.
        integrations: Channel credential management.
        directory: Areas and people address book.
        base_url: Resolved API origin used for requests.
        retry: Active :class:`~apruvly.RetryConfig` (throttle + backoff).
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
        accept_language: str | None = None,
        opener: OpenerDirector | None = None,
        urlopen_fn: Any | None = None,
        retry: RetryConfig | None = None,
        min_interval: float | None = None,
        max_retries: int | None = None,
        backoff_factor: float | None = None,
        backoff_max: float | None = None,
        retry_jitter: bool | None = None,
    ) -> None:
        """Create a client.

        Args:
            api_key: API key from the Apruvly dashboard (``wf-…``).
                Falls back to the ``APRUVLY_API_KEY`` environment variable.
            base_url: API origin. Defaults to ``APRUVLY_BASE_URL`` if set,
                otherwise ``https://api.apruvly.io``.
            timeout: Per-request timeout in seconds (default 30).
            user_agent: ``User-Agent`` header value.
            accept_language: Optional ``Accept-Language`` (e.g. ``en``, ``pt-BR``).
            opener: Optional custom :class:`urllib.request.OpenerDirector`.
            urlopen_fn: Optional replacement for :func:`urllib.request.urlopen`
                (primarily for tests).
            retry: Full throttle/retry policy. When omitted, conservative
                defaults are used and then overlaid with ``APRUVLY_*`` env vars.
            min_interval: Override for :attr:`RetryConfig.min_interval`.
            max_retries: Override for :attr:`RetryConfig.max_retries`.
            backoff_factor: Override for :attr:`RetryConfig.backoff_factor`.
            backoff_max: Override for :attr:`RetryConfig.backoff_max`.
            retry_jitter: Override for :attr:`RetryConfig.jitter`.
        """
        resolved_key = api_key if api_key is not None else os.environ.get("APRUVLY_API_KEY")
        if not resolved_key:
            raise ValueError(
                "api_key is required (pass Client(api_key=...) or set APRUVLY_API_KEY)"
            )

        if base_url is not None:
            resolved_base = base_url
        else:
            resolved_base = os.environ.get("APRUVLY_BASE_URL") or DEFAULT_BASE_URL

        from dataclasses import replace

        if retry is None:
            retry_cfg = RetryConfig.from_env()
        else:
            retry_cfg = retry
        overrides: dict[str, Any] = {}
        if min_interval is not None:
            overrides["min_interval"] = min_interval
        if max_retries is not None:
            overrides["max_retries"] = max_retries
        if backoff_factor is not None:
            overrides["backoff_factor"] = backoff_factor
        if backoff_max is not None:
            overrides["backoff_max"] = backoff_max
        if retry_jitter is not None:
            overrides["jitter"] = retry_jitter
        if overrides:
            retry_cfg = replace(retry_cfg, **overrides)

        self.base_url = resolved_base.rstrip("/")
        self.retry = retry_cfg
        self._http = Requestor(
            api_key=resolved_key,
            base_url=self.base_url,
            timeout=timeout,
            user_agent=user_agent,
            accept_language=accept_language,
            opener=opener,
            urlopen_fn=urlopen_fn,
            retry=retry_cfg,
        )
        self._system = SystemResource(self._http)
        self.workflows = WorkflowsResource(self._http)
        self.decisions = DecisionsResource(self._http)
        self.billing = BillingResource(self._http)
        self.integrations = IntegrationsResource(self._http)
        self.directory = DirectoryResource(self._http)

    def health(self) -> Any:
        """Check API liveness. Any authenticated key; no scope required."""
        return self._system.health()
