"""Throttle / retry / backoff behaviour."""

from __future__ import annotations

import unittest
from urllib.error import URLError

from apruvly import Client, QuotaExceededError, RetryConfig
from apruvly._http import Requestor, parse_retry_after
from tests import MockTransport


class RetryTests(unittest.TestCase):
    def test_retries_429_then_succeeds(self) -> None:
        transport = MockTransport()
        sleeps: list[float] = []
        transport.enqueue(
            429,
            {"success": False, "data": {"quota_type": "requests_per_minute", "limit": 10}},
            headers={"Retry-After": "2"},
        )
        transport.enqueue(200, {"success": True, "data": {"ok": True}})

        client = Client(
            api_key="wf-test",
            urlopen_fn=transport,
            retry=RetryConfig(
                min_interval=0,
                max_retries=2,
                backoff_factor=1.0,
                jitter=False,
            ),
        )
        # Inject deterministic sleep via Requestor
        client._http._sleep = sleeps.append  # type: ignore[method-assign]
        client._http._random = lambda: 0.5  # type: ignore[method-assign]

        client.health()
        self.assertEqual(len(transport.requests), 2)
        self.assertEqual(sleeps, [2.0])  # Retry-After wins over backoff

    def test_exhausts_retries_on_429(self) -> None:
        transport = MockTransport()
        for _ in range(3):
            transport.enqueue(
                429,
                {"success": False, "message": "slow down", "data": {"quota_type": "requests_per_minute", "limit": 10}},
            )
        sleeps: list[float] = []
        client = Client(
            api_key="wf-test",
            urlopen_fn=transport,
            retry=RetryConfig(min_interval=0, max_retries=2, backoff_factor=1.0, jitter=False),
        )
        client._http._sleep = sleeps.append  # type: ignore[method-assign]

        with self.assertRaises(QuotaExceededError):
            client.health()
        self.assertEqual(len(transport.requests), 3)
        self.assertEqual(sleeps, [1.0, 2.0])

    def test_does_not_retry_400(self) -> None:
        transport = MockTransport()
        transport.enqueue(400, {"success": False, "data": {"message": "bad"}})
        client = Client(
            api_key="wf-test",
            urlopen_fn=transport,
            retry=RetryConfig(min_interval=0, max_retries=3, jitter=False),
        )
        from apruvly import ValidationError

        with self.assertRaises(ValidationError):
            client.workflows.validate({"object": {"title": "x"}, "expires": "1h", "start": "a", "workflow": {}})
        self.assertEqual(len(transport.requests), 1)

    def test_retries_get_on_transport_error(self) -> None:
        transport = MockTransport()
        transport.enqueue(200, {"success": True, "data": {"ok": True}})
        calls = {"n": 0}

        def flaky(req, timeout=None, context=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise URLError("connection reset")
            return transport(req, timeout=timeout, context=context)

        sleeps: list[float] = []
        client = Client(
            api_key="wf-test",
            urlopen_fn=flaky,
            retry=RetryConfig(min_interval=0, max_retries=2, backoff_factor=0.5, jitter=False),
        )
        client._http._sleep = sleeps.append  # type: ignore[method-assign]
        client.health()
        self.assertEqual(calls["n"], 2)
        self.assertEqual(sleeps, [0.5])

    def test_does_not_retry_post_on_transport_error(self) -> None:
        def always_fail(req, timeout=None, context=None):
            raise URLError("connection reset")

        client = Client(
            api_key="wf-test",
            urlopen_fn=always_fail,
            retry=RetryConfig(min_interval=0, max_retries=3, jitter=False),
        )
        sleeps: list[float] = []
        client._http._sleep = sleeps.append  # type: ignore[method-assign]

        from apruvly import APIError

        with self.assertRaises(APIError):
            client.workflows.create(
                {
                    "object": {"title": "x"},
                    "expires": "1h",
                    "start": "mgr",
                    "workflow": {
                        "mgr": {
                            "type": "email",
                            "data": {
                                "to": ["a@x.com"],
                                "subject": "s",
                                "body": "${approve_link} ${reject_link}",
                            },
                        }
                    },
                }
            )
        self.assertEqual(sleeps, [])  # no retry for POST transport errors

    def test_throttle_spaces_requests(self) -> None:
        transport = MockTransport()
        transport.enqueue(200, {"success": True, "data": {}})
        transport.enqueue(200, {"success": True, "data": {}})
        clock = {"t": 100.0}
        sleeps: list[float] = []

        def fake_clock() -> float:
            return clock["t"]

        def fake_sleep(seconds: float) -> None:
            sleeps.append(seconds)
            clock["t"] += seconds

        client = Client(
            api_key="wf-test",
            urlopen_fn=transport,
            retry=RetryConfig(min_interval=0.2, max_retries=0, jitter=False),
        )
        client._http._clock = fake_clock  # type: ignore[method-assign]
        client._http._sleep = fake_sleep  # type: ignore[method-assign]

        client.health()
        client.health()
        self.assertEqual(len(sleeps), 1)
        self.assertAlmostEqual(sleeps[0], 0.2, places=6)

    def test_parse_retry_after(self) -> None:
        from email.message import Message

        hdrs = Message()
        hdrs["Retry-After"] = "5"
        self.assertEqual(parse_retry_after(hdrs, fallback=1.0, cap=30.0), 5.0)
        hdrs2 = Message()
        hdrs2["Retry-After"] = "999"
        self.assertEqual(parse_retry_after(hdrs2, fallback=1.0, cap=30.0), 30.0)

    def test_jitter_reduces_delay(self) -> None:
        req = Requestor(
            api_key="wf-x",
            retry=RetryConfig(jitter=True, min_interval=0, max_retries=0),
            random_fn=lambda: 0.25,
        )
        self.assertEqual(req._with_jitter(4.0), 1.0)

    def test_client_kwarg_overrides(self) -> None:
        client = Client(
            api_key="wf-x",
            urlopen_fn=MockTransport(),
            min_interval=0.5,
            max_retries=1,
            retry_jitter=False,
        )
        self.assertEqual(client.retry.min_interval, 0.5)
        self.assertEqual(client.retry.max_retries, 1)
        self.assertFalse(client.retry.jitter)


if __name__ == "__main__":
    unittest.main()
