"""Model serialization / builder tests."""

from __future__ import annotations

import unittest

from apruvly.models import (
    SMTPIntegrationConfig,
    WorkflowConfig,
    WorkflowObject,
    WorkflowStatus,
    email_step,
    webhook_action,
)
from apruvly.models.workflow import Step


class ModelTests(unittest.TestCase):
    def test_workflow_config_roundtrip(self) -> None:
        cfg = WorkflowConfig(
            object=WorkflowObject(title="Q1 Budget", tags=["finance"]),
            expires="24h",
            start="manager",
            workflow={
                "manager": email_step(
                    to=["boss@example.com"],
                    subject="Please approve",
                    body="Approve: ${approve_link} Reject: ${reject_link}",
                )
            },
            on={
                "workflow_approved": [
                    webhook_action(
                        url="https://example.com/hook",
                        body={"id": "${id}", "status": "${status}"},
                    )
                ]
            },
            external_id="BUDGET-1",
        )
        payload = cfg.to_dict()
        self.assertEqual(payload["object"]["title"], "Q1 Budget")
        self.assertEqual(payload["workflow"]["manager"]["type"], "email")
        self.assertEqual(payload["on"]["workflow_approved"][0]["type"], "webhook")
        restored = WorkflowConfig.from_dict(payload)
        self.assertEqual(restored.external_id, "BUDGET-1")
        self.assertIsInstance(restored.workflow["manager"], Step)

    def test_workflow_status_camel_case(self) -> None:
        status = WorkflowStatus.from_dict(
            {
                "id": "w-1",
                "externalId": "E-1",
                "status": "pending",
                "currentStep": "manager",
                "createdAt": "2026-01-01T00:00:00Z",
                "expiresAt": "2026-01-02T00:00:00Z",
                "decisions": [{"user": "a@x.com", "is_approved": True}],
                "currentApprovers": {
                    "a@x.com": {"challenge": "c-1", "is_approved": None}
                },
            }
        )
        self.assertEqual(status.externalId, "E-1")
        self.assertEqual(status.currentStep, "manager")
        self.assertEqual(status.decisions[0].user, "a@x.com")
        self.assertEqual(status.currentApprovers["a@x.com"].challenge, "c-1")

    def test_smtp_from_alias(self) -> None:
        cfg = SMTPIntegrationConfig(host="smtp.example.com", port=587, from_="noreply@example.com")
        payload = cfg.to_dict()
        self.assertEqual(payload["from"], "noreply@example.com")
        self.assertNotIn("from_", payload)


if __name__ == "__main__":
    unittest.main()
