"""HTTP / exception mapping tests."""

from __future__ import annotations

import json
import os
import unittest

from apruvly import (
    AuthError,
    Client,
    ForbiddenError,
    NotFoundError,
    PaymentRequiredError,
    QuotaExceededError,
    RetryConfig,
    ValidationError,
)
from tests import MockTransport

_FAST = RetryConfig.disabled()


class HttpClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = MockTransport()
        self.client = Client(
            api_key="wf-testkey",
            urlopen_fn=self.transport,
            retry=_FAST,
        )

    def test_bearer_and_user_agent(self) -> None:
        self.transport.enqueue(200, {"success": True, "data": {"ok": True}})
        self.client.health()
        req = self.transport.last
        headers = {k.lower(): v for k, v in req.header_items()}
        self.assertEqual(headers.get("authorization"), "Bearer wf-testkey")
        self.assertIn("Apruvly Client Python", headers.get("user-agent", ""))
        self.assertTrue(req.full_url.endswith("/api/v1/health"))

    def test_create_workflow_202(self) -> None:
        self.transport.enqueue(
            202,
            {"success": True, "data": {"id": "w-1", "externalId": "EXT-1"}},
        )
        created = self.client.workflows.create(
            {
                "object": {"title": "Budget"},
                "expires": "24h",
                "start": "manager",
                "workflow": {
                    "manager": {
                        "type": "email",
                        "data": {
                            "to": ["a@example.com"],
                            "subject": "Approve",
                            "body": "${approve_link} ${reject_link}",
                        },
                    }
                },
            }
        )
        self.assertEqual(created.id, "w-1")
        self.assertEqual(created.externalId, "EXT-1")
        req = self.transport.last
        self.assertEqual(req.get_method(), "POST")
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["object"]["title"], "Budget")

    def test_auth_error_401(self) -> None:
        self.transport.enqueue(
            401,
            {"success": False, "data": {"message": "bad key", "errorCode": "unauthorized"}},
        )
        with self.assertRaises(AuthError) as ctx:
            self.client.health()
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.error_code, "unauthorized")

    def test_forbidden_403(self) -> None:
        self.transport.enqueue(
            403,
            {"success": False, "message": "missing scope"},
        )
        with self.assertRaises(ForbiddenError):
            self.client.workflows.get("abc")

    def test_not_found_404(self) -> None:
        self.transport.enqueue(
            404,
            {"success": False, "data": {"message": "missing"}},
        )
        with self.assertRaises(NotFoundError):
            self.client.workflows.get("missing")

    def test_payment_required_402(self) -> None:
        self.transport.enqueue(
            402,
            {
                "success": False,
                "data": {
                    "message": "no credits",
                    "errorCode": "insufficient_credits",
                },
            },
        )
        with self.assertRaises(PaymentRequiredError) as ctx:
            self.client.workflows.create({"object": {"title": "x"}, "expires": "1h", "start": "a", "workflow": {}})
        self.assertEqual(ctx.exception.error_code, "insufficient_credits")

    def test_quota_429(self) -> None:
        self.transport.enqueue(
            429,
            {
                "success": False,
                "message": "slow down",
                "data": {"quota_type": "requests_per_minute", "limit": 100},
            },
        )
        with self.assertRaises(QuotaExceededError) as ctx:
            self.client.workflows.recent()
        self.assertEqual(ctx.exception.quota_type, "requests_per_minute")
        self.assertEqual(ctx.exception.limit, 100)

    def test_validation_400(self) -> None:
        self.transport.enqueue(
            400,
            {
                "success": False,
                "data": {
                    "message": "bad field",
                    "field": "expires",
                    "errorCode": "invalid_parameter",
                },
            },
        )
        with self.assertRaises(ValidationError) as ctx:
            self.client.workflows.validate({"object": {"title": "x"}, "expires": "1s", "start": "a", "workflow": {}})
        self.assertEqual(ctx.exception.field, "expires")

    def test_integration_upsert_204(self) -> None:
        self.transport.enqueue(204)
        result = self.client.integrations.upsert(
            "telegram",
            {"botToken": "123:abc"},
        )
        self.assertIsNone(result)
        self.assertEqual(self.transport.last.get_method(), "PUT")

    def test_path_escape_external_id(self) -> None:
        self.transport.enqueue(
            200,
            {
                "success": True,
                "data": {"id": "w-1", "status": "pending", "currentStep": "m"},
            },
        )
        self.client.workflows.get_by_external_id("a/b:c")
        self.assertIn("/workflow/external/a%2Fb%3Ac", self.transport.last.full_url)

    def test_search_query_params(self) -> None:
        self.transport.enqueue(
            200,
            {
                "success": True,
                "data": [
                    {
                        "id": "w-1",
                        "title": "T",
                        "current_status": "pending",
                        "current_step": "manager",
                    }
                ],
            },
        )
        rows = self.client.workflows.search(query="budget", status="pending", limit=10, tags=["a", "b"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].title, "T")
        url = self.transport.last.full_url
        self.assertIn("query=budget", url)
        self.assertIn("status=pending", url)
        self.assertIn("limit=10", url)
        self.assertIn("tags=a%2Cb", url)

    def test_custom_base_url(self) -> None:
        transport = MockTransport()
        client = Client(
            api_key="wf-test",
            base_url="http://localhost:1509/",
            urlopen_fn=transport,
            retry=_FAST,
        )
        self.assertEqual(client.base_url, "http://localhost:1509")
        transport.enqueue(200, {"success": True, "data": {"ok": True}})
        client.health()
        self.assertTrue(
            transport.last.full_url.startswith("http://localhost:1509/api/v1/health")
        )

    def test_base_url_from_env(self) -> None:
        transport = MockTransport()
        previous = os.environ.get("APRUVLY_BASE_URL")
        os.environ["APRUVLY_BASE_URL"] = "https://staging.example.com"
        try:
            client = Client(api_key="wf-test", urlopen_fn=transport, retry=_FAST)
            self.assertEqual(client.base_url, "https://staging.example.com")
        finally:
            if previous is None:
                os.environ.pop("APRUVLY_BASE_URL", None)
            else:
                os.environ["APRUVLY_BASE_URL"] = previous


if __name__ == "__main__":
    unittest.main()
