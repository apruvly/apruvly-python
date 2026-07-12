"""Low-level HTTP transport for the Apruvly API (stdlib only)."""

from __future__ import annotations

import json
import random
import ssl
import time
from collections.abc import Callable, Mapping
from email.message import Message
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin
from urllib.request import OpenerDirector, Request, build_opener, urlopen

from apruvly._retry import RetryConfig
from apruvly._version import __version__
from apruvly.exceptions import (
    APIError,
    AuthError,
    ConflictError,
    ForbiddenError,
    NotAcceptableError,
    NotFoundError,
    PaymentRequiredError,
    QuotaExceededError,
    ValidationError,
)

DEFAULT_BASE_URL = "https://api.apruvly.io"
DEFAULT_TIMEOUT = 30.0
DEFAULT_USER_AGENT = f"Apruvly Client Python/{__version__}"

JsonBody = Mapping[str, Any] | list[Any] | None
QueryParams = Mapping[str, Any] | None
SleepFn = Callable[[float], None]
ClockFn = Callable[[], float]
RandomFn = Callable[[], float]


def path_escape(segment: str) -> str:
    """Percent-encode a single URL path segment."""
    return quote(str(segment), safe="")


def _omit_none(params: Mapping[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            out[key] = "true" if value else "false"
        else:
            out[key] = str(value)
    return out


def _extract_message(payload: Any, fallback: str) -> str:
    if not isinstance(payload, dict):
        return fallback
    top = payload.get("message")
    if isinstance(top, str) and top:
        return top
    data = payload.get("data")
    if isinstance(data, dict):
        nested = data.get("message")
        if isinstance(nested, str) and nested:
            return nested
    return fallback


def _header_get(headers: Any, name: str) -> str | None:
    if headers is None:
        return None
    getter = getattr(headers, "get", None)
    if callable(getter):
        value = getter(name) or getter(name.lower()) or getter(name.title())
        if value is not None:
            return str(value)
    if isinstance(headers, Mapping):
        for key, value in headers.items():
            if str(key).lower() == name.lower():
                return str(value)
    return None


def parse_retry_after(headers: Any, *, fallback: float, cap: float) -> float:
    """Parse ``Retry-After`` (delta-seconds). Falls back to ``fallback``, capped."""
    raw = _header_get(headers, "Retry-After")
    delay = fallback
    if raw is not None:
        try:
            delay = float(raw.strip())
        except ValueError:
            delay = fallback
    if delay < 0:
        delay = fallback
    return min(delay, cap) if cap > 0 else delay


def _raise_for_response(status: int, payload: Any, raw_body: bytes) -> None:
    data = payload.get("data") if isinstance(payload, dict) else None
    message = _extract_message(payload, f"HTTP {status}")
    error_code: str | None = None
    field: str | None = None
    parameter: str | None = None
    integration: str | None = None
    quota_type: str | None = None
    limit: int | None = None

    if isinstance(data, dict):
        code = data.get("errorCode")
        if isinstance(code, str):
            error_code = code
        field_val = data.get("field")
        if isinstance(field_val, str):
            field = field_val
        param_val = data.get("parameter")
        if isinstance(param_val, str):
            parameter = param_val
        integ = data.get("integration")
        if isinstance(integ, str):
            integration = integ
        qt = data.get("quota_type")
        if isinstance(qt, str):
            quota_type = qt
        lim = data.get("limit")
        if isinstance(lim, int):
            limit = lim

    if status == 401:
        raise AuthError(message, status_code=status, error_code=error_code, data=data)
    if status == 403:
        raise ForbiddenError(message, status_code=status, error_code=error_code, data=data)
    if status == 404:
        raise NotFoundError(message, status_code=status, error_code=error_code, data=data)
    if status == 402:
        raise PaymentRequiredError(
            message, status_code=status, error_code=error_code, data=data
        )
    if status == 409:
        raise ConflictError(message, status_code=status, error_code=error_code, data=data)
    if status == 406:
        raise NotAcceptableError(
            message, status_code=status, error_code=error_code, data=data
        )
    if status == 429 or quota_type is not None:
        raise QuotaExceededError(
            message,
            status_code=status,
            error_code=error_code,
            data=data,
            quota_type=quota_type,
            limit=limit,
        )
    if status in (400, 422):
        raise ValidationError(
            message,
            status_code=status,
            error_code=error_code,
            data=data,
            field=field,
            parameter=parameter,
            integration=integration,
        )

    body_preview = raw_body.decode("utf-8", errors="replace")[:500]
    raise APIError(
        message or f"Unexpected HTTP {status}: {body_preview}",
        status_code=status,
        error_code=error_code,
        data=data,
    )


class Requestor:
    """Performs authenticated JSON requests against the Apruvly API."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
        accept_language: str | None = None,
        opener: OpenerDirector | None = None,
        urlopen_fn: Callable[..., Any] | None = None,
        retry: RetryConfig | None = None,
        sleep_fn: SleepFn | None = None,
        clock_fn: ClockFn | None = None,
        random_fn: RandomFn | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.user_agent = user_agent
        self.accept_language = accept_language
        self._opener = opener
        self._urlopen = urlopen_fn or urlopen
        self.retry = retry if retry is not None else RetryConfig.from_env()
        self._sleep: SleepFn = sleep_fn or time.sleep
        self._clock: ClockFn = clock_fn or time.monotonic
        self._random: RandomFn = random_fn or random.random
        self._next_slot = 0.0

    def request(
        self,
        method: str,
        path: str,
        *,
        body: JsonBody = None,
        params: QueryParams = None,
        expected_statuses: tuple[int, ...] = (200,),
        unwrap: bool = True,
    ) -> Any:
        """Send an HTTP request and return unwrapped ``data`` (or ``None`` for 204).

        Applies client-side throttling and conservative retries (see
        :class:`~apruvly.RetryConfig`).

        Args:
            method: HTTP method.
            path: Absolute path beginning with ``/api/v1``.
            body: JSON-serializable request body.
            params: Query string parameters (``None`` values omitted).
            expected_statuses: Status codes treated as success.
            unwrap: When True, parse the API envelope and return ``data``.

        Returns:
            Unwrapped ``data`` field, full JSON payload when ``unwrap`` is False,
            or ``None`` for empty 204 responses.

        Raises:
            ApruvlyError: Mapped API or transport failure after retries are
                exhausted.
        """
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        if params:
            query = urlencode(_omit_none(params))
            if query:
                url = f"{url}?{query}"

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": self.user_agent,
        }
        if self.accept_language:
            headers["Accept-Language"] = self.accept_language

        data: bytes | None = None
        if body is not None:
            data = json.dumps(body, separators=(",", ":"), default=str).encode("utf-8")
            headers["Content-Type"] = "application/json"

        method_u = method.upper()
        attempts = self.retry.max_retries + 1
        last_error: BaseException | None = None

        for attempt in range(attempts):
            self._throttle()
            req = Request(url, data=data, headers=headers, method=method_u)
            try:
                return self._dispatch(req, expected_statuses=expected_statuses, unwrap=unwrap)
            except HTTPError as exc:
                raw, payload = self._read_http_error(exc)
                status = exc.code
                if (
                    attempt + 1 < attempts
                    and status in self.retry.retry_statuses
                ):
                    delay = self._backoff_delay(attempt)
                    if status == 429:
                        delay = parse_retry_after(
                            exc.headers,
                            fallback=delay,
                            cap=self.retry.backoff_max,
                        )
                    self._sleep(self._with_jitter(delay))
                    last_error = exc
                    continue
                _raise_for_response(status, payload, raw)
                raise  # pragma: no cover
            except URLError as exc:
                if attempt + 1 < attempts and self._should_retry_transport(method_u, exc):
                    self._sleep(self._with_jitter(self._backoff_delay(attempt)))
                    last_error = exc
                    continue
                raise APIError(f"Transport error: {exc.reason}") from exc
            except TimeoutError as exc:
                if (
                    attempt + 1 < attempts
                    and self.retry.retry_on_timeout
                    and method_u in self.retry.retry_transport_methods
                ):
                    self._sleep(self._with_jitter(self._backoff_delay(attempt)))
                    last_error = exc
                    continue
                raise APIError(f"Transport error: {exc}") from exc

        if last_error is not None:
            if isinstance(last_error, HTTPError):
                raw, payload = self._read_http_error(last_error)
                _raise_for_response(last_error.code, payload, raw)
            raise APIError(f"Transport error: {last_error}") from last_error
        raise APIError("Request failed after retries")  # pragma: no cover

    def _dispatch(
        self,
        req: Request,
        *,
        expected_statuses: tuple[int, ...],
        unwrap: bool,
    ) -> Any:
        try:
            if self._opener is not None:
                response = self._opener.open(req, timeout=self.timeout)
            else:
                context = ssl.create_default_context()
                response = self._urlopen(req, timeout=self.timeout, context=context)
        except HTTPError:
            raise
        except URLError:
            raise

        with response:
            status = getattr(response, "status", None) or response.getcode()
            raw = response.read()

        if status == 204:
            if status not in expected_statuses and 204 not in expected_statuses:
                _raise_for_response(status, None, raw)
            return None

        payload = self._safe_json(raw) if raw else None

        if status not in expected_statuses:
            # Re-raise as HTTPError-shaped path via mapping helper.
            _raise_for_response(status, payload, raw)

        if not unwrap:
            return payload

        if not isinstance(payload, dict):
            raise APIError(
                "Expected JSON object response envelope",
                status_code=status,
                data=payload,
            )

        if payload.get("success") is False:
            _raise_for_response(status, payload, raw)

        return payload.get("data")

    def _throttle(self) -> None:
        interval = self.retry.min_interval
        if interval <= 0:
            return
        now = self._clock()
        wait = self._next_slot - now
        if wait > 0:
            self._sleep(wait)
            now = self._clock()
        self._next_slot = now + interval

    def _backoff_delay(self, attempt: int) -> float:
        # attempt is 0-based index of the failed try.
        delay = self.retry.backoff_factor * (2**attempt)
        if self.retry.backoff_max > 0:
            delay = min(delay, self.retry.backoff_max)
        return delay

    def _with_jitter(self, delay: float) -> float:
        if delay <= 0:
            return 0.0
        if not self.retry.jitter:
            return delay
        # Full jitter: sleep in [0, delay].
        return delay * self._random()

    def _should_retry_transport(self, method: str, exc: URLError) -> bool:
        if method not in self.retry.retry_transport_methods:
            return False
        if not self.retry.retry_on_timeout:
            reason = exc.reason
            if isinstance(reason, TimeoutError) or (
                isinstance(reason, OSError) and "timed out" in str(reason).lower()
            ):
                return False
        return True

    @staticmethod
    def _read_http_error(exc: HTTPError) -> tuple[bytes, Any]:
        try:
            raw = exc.read() if hasattr(exc, "read") else b""
        finally:
            try:
                exc.close()
            except Exception:
                pass
        return raw, Requestor._safe_json(raw)

    @staticmethod
    def _safe_json(raw: bytes) -> Any:
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None


def build_default_opener() -> OpenerDirector:
    """Create a default urllib opener (handy for tests and custom handlers)."""
    return build_opener()


def message_headers(**headers: str) -> Message:
    """Build an :class:`email.message.Message` header map (tests / helpers)."""
    msg = Message()
    for key, value in headers.items():
        msg[key] = value
    return msg
