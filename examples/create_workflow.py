#!/usr/bin/env python3
"""Create a simple email approval workflow.

Usage:
    export APRUVLY_API_KEY=wf-...
    python examples/create_workflow.py
"""

from __future__ import annotations

import os
import sys

from apruvly import Client, ValidationError
from apruvly.models import WorkflowConfig, WorkflowObject, email_step, webhook_action


def main() -> int:
    if not os.environ.get("APRUVLY_API_KEY"):
        print("Set APRUVLY_API_KEY to a wf-… key from the Apruvly dashboard.", file=sys.stderr)
        return 1

    # Reads APRUVLY_API_KEY and optional APRUVLY_BASE_URL from the environment.
    client = Client()
    print(f"Using API {client.base_url}", file=sys.stderr)

    config = WorkflowConfig(
        object=WorkflowObject(
            title="Example budget approval",
            description="Created by the Apruvly Python SDK example",
            tags=["example"],
        ),
        expires="24h",
        start="manager",
        workflow={
            "manager": email_step(
                to=[os.environ.get("APRUVLY_APPROVER_EMAIL", "you@example.com")],
                subject="Please approve the example budget",
                body=(
                    "Hello,\n\n"
                    "Approve: ${approve_link}\n"
                    "Reject: ${reject_link}\n"
                ),
            )
        },
        on={
            "workflow_completed": [
                webhook_action(
                    url=os.environ.get(
                        "APRUVLY_WEBHOOK_URL",
                        "https://example.com/apruvly-hook",
                    ),
                    body={"workflow_id": "${id}", "status": "${status}"},
                )
            ]
        },
    )

    try:
        client.workflows.validate(config)
        created = client.workflows.create(config)
    except ValidationError as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Created workflow {created.id}")
    status = client.workflows.get(created.id)
    print(f"Status={status.status} step={status.currentStep}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
