"""Resource coverage for billing, decisions, directory."""

from __future__ import annotations

import json
import unittest

from apruvly import Client, RetryConfig
from apruvly.models import DirectoryAreaInput, DirectoryPersonInput, SlackIntegrationConfig
from tests import MockTransport

_FAST = RetryConfig.disabled()


class ResourcesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = MockTransport()
        self.client = Client(api_key="wf-test", urlopen_fn=self.transport, retry=_FAST)

    def test_billing_get(self) -> None:
        self.transport.enqueue(
            200,
            {
                "success": True,
                "data": {
                    "balance": 42,
                    "plan": {"name": "Growth", "id": 3},
                    "usage": {"active_workflows": 1},
                    "recent_transactions": [{"amount": -2, "reason": "workflow"}],
                },
            },
        )
        info = self.client.billing.get()
        self.assertEqual(info.balance, 42)
        self.assertEqual(info.plan.name if info.plan else None, "Growth")
        self.assertEqual(info.recent_transactions[0].amount, -2)

    def test_approve_with_comment(self) -> None:
        self.transport.enqueue(200, {"success": True, "data": {}})
        self.client.decisions.approve("w-1", "c-1", comment="LGTM")
        req = self.transport.last
        self.assertEqual(req.get_method(), "PUT")
        self.assertTrue(req.full_url.endswith("/workflow/w-1/c-1/approve"))
        self.assertEqual(json.loads(req.data.decode()), {"comment": "LGTM"})

    def test_directory_people_list(self) -> None:
        self.transport.enqueue(
            200,
            {
                "success": True,
                "data": {
                    "items": [
                        {
                            "id": "p-1",
                            "display_name": "Ada",
                            "contacts": [
                                {"provider": "email", "address": "ada@example.com"}
                            ],
                        }
                    ],
                    "total": 1,
                    "page": 1,
                    "page_size": 25,
                },
            },
        )
        result = self.client.directory.people.list(page=1, q="Ada")
        self.assertEqual(result.total, 1)
        self.assertEqual(result.items[0].display_name, "Ada")
        self.assertEqual(result.items[0].contacts[0].provider, "email")

    def test_directory_area_create(self) -> None:
        self.transport.enqueue(
            201,
            {"success": True, "data": {"id": "a-1", "name": "Finance", "is_active": True}},
        )
        area = self.client.directory.areas.create(DirectoryAreaInput(name="Finance"))
        self.assertEqual(area.id, "a-1")

    def test_integrations_list_and_typed_upsert(self) -> None:
        self.transport.enqueue(
            200,
            {
                "success": True,
                "data": [
                    {"integration": "slack", "configured": True, "hasBotToken": True}
                ],
            },
        )
        items = self.client.integrations.list()
        self.assertEqual(items[0].integration, "slack")
        self.assertTrue(items[0].get("hasBotToken"))

        self.transport.enqueue(204)
        self.client.integrations.upsert(
            "slack",
            SlackIntegrationConfig(botToken="xoxb-1", signingSecret="sec"),
        )
        body = json.loads(self.transport.last.data.decode())
        self.assertEqual(body["botToken"], "xoxb-1")

    def test_person_input_serialization(self) -> None:
        self.transport.enqueue(
            201,
            {
                "success": True,
                "data": {"id": "p-2", "display_name": "Grace", "area_ids": [], "contacts": []},
            },
        )
        person = self.client.directory.people.create(
            DirectoryPersonInput(display_name="Grace")
        )
        self.assertEqual(person.display_name, "Grace")


if __name__ == "__main__":
    unittest.main()
