"""Shared HTTP mock helpers for unittest."""

from __future__ import annotations

import io
import json
from email.message import Message
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request


class MockResponse:
    def __init__(self, body: bytes, status: int = 200, headers: dict | None = None):
        self._body = body
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}

    def read(self) -> bytes:
        return self._body

    def getcode(self) -> int:
        return self.status

    def __enter__(self) -> MockResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class MockTransport:
    """Records requests and returns scripted responses."""

    def __init__(self) -> None:
        self.requests: list[Request] = []
        self._queue: list[tuple[int, bytes, Message | None]] = []

    def enqueue(
        self,
        status: int,
        payload: Any = None,
        *,
        raw: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        if raw is not None:
            body = raw
        elif payload is None and status == 204:
            body = b""
        else:
            body = (
                json.dumps(payload).encode("utf-8") if payload is not None else b""
            )
        hdrs: Message | None = None
        if headers:
            hdrs = Message()
            for key, value in headers.items():
                hdrs[key] = value
        self._queue.append((status, body, hdrs))

    def __call__(self, req: Request, timeout: float | None = None, context: Any = None):
        self.requests.append(req)
        if not self._queue:
            raise AssertionError(f"Unexpected request: {req.get_method()} {req.full_url}")
        status, raw, hdrs = self._queue.pop(0)
        if status >= 400:
            raise HTTPError(
                req.full_url,
                status,
                "error",
                hdrs=hdrs or Message(),
                fp=io.BytesIO(raw),
            )
        return MockResponse(raw, status=status)

    @property
    def last(self) -> Request:
        return self.requests[-1]
