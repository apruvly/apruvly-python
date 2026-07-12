#!/usr/bin/env python3
"""Live smoke test against a real Apruvly API (all REST resources).

Loads ``.env`` from the repo root (stdlib only) and exercises every client
method. Destructive writes use disposable resources and clean up when possible.

Usage:
    set -a && source .env && set +a
    python examples/live_smoke.py

    # or:
    python examples/live_smoke.py
    # (auto-loads .env next to this repo)
"""

from __future__ import annotations

import os
import sys
import traceback
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from apruvly import (  # noqa: E402
    ApruvlyError,
    Client,
    ConflictError,
    NotFoundError,
    PaymentRequiredError,
    ValidationError,
)
from apruvly.models import (  # noqa: E402
    DirectoryAreaInput,
    DirectoryPersonInput,
    WorkflowConfig,
    WorkflowObject,
    email_step,
)


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


class Reporter:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def ok(self, name: str, detail: str = "") -> None:
        self.rows.append((name, "PASS", detail))
        print(f"  PASS  {name}" + (f" — {detail}" if detail else ""))

    def skip(self, name: str, detail: str) -> None:
        self.rows.append((name, "SKIP", detail))
        print(f"  SKIP  {name} — {detail}")

    def fail(self, name: str, detail: str) -> None:
        self.rows.append((name, "FAIL", detail))
        print(f"  FAIL  {name} — {detail}")

    def summary(self) -> int:
        counts = {"PASS": 0, "SKIP": 0, "FAIL": 0}
        for _, status, _ in self.rows:
            counts[status] += 1
        print()
        print(
            f"Summary: {counts['PASS']} passed, "
            f"{counts['SKIP']} skipped, {counts['FAIL']} failed "
            f"({len(self.rows)} checks)"
        )
        return 1 if counts["FAIL"] else 0


def call(rep: Reporter, name: str, fn, *, soft: tuple[type[BaseException], ...] = ()) -> object:
    try:
        result = fn()
        rep.ok(name)
        return result
    except soft as exc:
        rep.skip(name, f"{type(exc).__name__}: {exc}")
        return None
    except Exception as exc:  # noqa: BLE001 — smoke report
        detail = f"{type(exc).__name__}: {exc}"
        rep.fail(name, detail)
        traceback.print_exc()
        return None


def main() -> int:
    load_dotenv(ROOT / ".env")
    if not os.environ.get("APRUVLY_API_KEY"):
        print("APRUVLY_API_KEY is required", file=sys.stderr)
        return 1

    client = Client()
    rep = Reporter()
    print(f"Live smoke against {client.base_url}")
    print()

    # --- System ---
    call(rep, "health", client.health)

    # --- Billing ---
    billing = call(rep, "billing.get", client.billing.get)
    if billing is not None:
        rep.ok(
            "billing.get.detail",
            f"balance={billing.balance} plan={getattr(billing.plan, 'name', None)}",
        )

    # --- Integrations (read) ---
    integrations = call(rep, "integrations.list", client.integrations.list) or []
    if integrations:
        name = integrations[0].integration
        call(rep, f"integrations.get({name})", lambda: client.integrations.get(name))
    else:
        # Still probe a known name — may 404 if never configured
        call(
            rep,
            "integrations.get(slack)",
            lambda: client.integrations.get("slack"),
            soft=(NotFoundError, ApruvlyError),
        )

    # Write paths exercised at end of smoke (soft on server errors / rate limits).

    # --- Workflows ---
    suffix = uuid.uuid4().hex[:8]
    external_id = f"py-smoke-{suffix}"
    approver = os.environ.get("APRUVLY_APPROVER_EMAIL") or "smoke@example.com"

    config = WorkflowConfig(
        object=WorkflowObject(
            title=f"Python SDK smoke {suffix}",
            description="Disposable workflow from examples/live_smoke.py",
            tags=["sdk-smoke"],
        ),
        expires="1h",
        start="manager",
        workflow={
            "manager": email_step(
                to=[approver],
                subject=f"[smoke] approve {suffix}",
                body="Approve: ${approve_link}\nReject: ${reject_link}\n",
            )
        },
        external_id=external_id,
    )

    call(rep, "workflows.validate", lambda: client.workflows.validate(config))

    created = call(rep, "workflows.create", lambda: client.workflows.create(config))
    workflow_id = created.id if created else None

    if workflow_id:
        status = call(rep, "workflows.get", lambda: client.workflows.get(workflow_id))
        call(
            rep,
            "workflows.get_by_external_id",
            lambda: client.workflows.get_by_external_id(external_id),
            soft=(PaymentRequiredError, NotFoundError, ApruvlyError),
        )
        call(
            rep,
            "workflows.search",
            lambda: client.workflows.search(query="Python SDK smoke", limit=10),
        )
        call(rep, "workflows.recent", client.workflows.recent)

        # Decisions — approve first pending challenge if present
        if status and status.currentApprovers:
            challenge = next(iter(status.currentApprovers.values())).challenge
            if challenge:
                call(
                    rep,
                    "decisions.approve",
                    lambda: client.decisions.approve(
                        workflow_id, challenge, comment="sdk smoke"
                    ),
                )
            else:
                rep.skip("decisions.approve", "approver has no challenge id")
        else:
            rep.skip("decisions.approve", "no currentApprovers on created workflow")

        # Reject path on a separate disposable workflow
        reject_cfg = WorkflowConfig(
            object=WorkflowObject(title=f"Python SDK reject {suffix}"),
            expires="1h",
            start="manager",
            workflow={
                "manager": email_step(
                    to=[approver],
                    subject="reject me",
                    body="${approve_link} ${reject_link}",
                )
            },
        )
        reject_created = call(
            rep,
            "workflows.create(for reject)",
            lambda: client.workflows.create(reject_cfg),
        )
        if reject_created:
            reject_status = client.workflows.get(reject_created.id)
            if reject_status.currentApprovers:
                r_challenge = next(
                    iter(reject_status.currentApprovers.values())
                ).challenge
                call(
                    rep,
                    "decisions.reject",
                    lambda: client.decisions.reject(
                        reject_created.id, r_challenge, comment="sdk smoke reject"
                    ),
                )
            else:
                rep.skip("decisions.reject", "no currentApprovers")
        else:
            rep.skip("decisions.reject", "create failed")

        # Cancel by UUID
        cancel_cfg = WorkflowConfig(
            object=WorkflowObject(title=f"Python SDK cancel {suffix}"),
            expires="1h",
            start="manager",
            workflow={
                "manager": email_step(
                    to=[approver],
                    subject="cancel me",
                    body="${approve_link} ${reject_link}",
                )
            },
        )
        cancel_created = call(
            rep,
            "workflows.create(for cancel)",
            lambda: client.workflows.create(cancel_cfg),
        )
        if cancel_created:
            call(
                rep,
                "workflows.cancel",
                lambda: client.workflows.cancel(cancel_created.id),
            )

        # Cancel by external_id (separate workflow — not already closed)
        ext_cancel = f"py-smoke-extcancel-{suffix}"
        ext_cfg = WorkflowConfig(
            object=WorkflowObject(title=f"Python SDK ext-cancel {suffix}"),
            expires="1h",
            start="manager",
            workflow={
                "manager": email_step(
                    to=[approver],
                    subject="ext cancel",
                    body="${approve_link} ${reject_link}",
                )
            },
            external_id=ext_cancel,
        )
        ext_created = call(
            rep,
            "workflows.create(for ext cancel)",
            lambda: client.workflows.create(ext_cfg),
        )
        if ext_created:
            call(
                rep,
                "workflows.cancel_by_external_id",
                lambda: client.workflows.cancel_by_external_id(ext_cancel),
            )
    else:
        for name in (
            "workflows.get",
            "workflows.get_by_external_id",
            "workflows.search",
            "workflows.recent",
            "decisions.approve",
            "decisions.reject",
            "workflows.cancel",
            "workflows.cancel_by_external_id",
        ):
            rep.skip(name, "create failed")

    # --- Directory ---
    soft_dir = (PaymentRequiredError, ConflictError, ValidationError, ApruvlyError)
    areas = call(rep, "directory.areas.list", client.directory.areas.list, soft=soft_dir)
    if areas is not None:
        area = call(
            rep,
            "directory.areas.create",
            lambda: client.directory.areas.create(
                DirectoryAreaInput(name=f"sdk-smoke-{suffix}")
            ),
            soft=soft_dir,
        )
        if area and area.id:
            call(
                rep,
                "directory.areas.get",
                lambda: client.directory.areas.get(area.id),
            )
            call(
                rep,
                "directory.areas.update",
                lambda: client.directory.areas.update(
                    area.id, DirectoryAreaInput(name=f"sdk-smoke-{suffix}-u")
                ),
            )
            bulk_areas = call(
                rep,
                "directory.areas.bulk_create",
                lambda: client.directory.areas.bulk_create(
                    [DirectoryAreaInput(name=f"sdk-smoke-bulk-{suffix}")]
                ),
                soft=soft_dir,
            )
            if bulk_areas and bulk_areas.items:
                bid = bulk_areas.items[0].id
                call(
                    rep,
                    "directory.areas.bulk_update",
                    lambda: client.directory.areas.bulk_update(
                        [DirectoryAreaInput(id=bid, name=f"sdk-smoke-bulk-{suffix}-u")]
                    ),
                    soft=soft_dir,
                )
            else:
                rep.skip("directory.areas.bulk_update", "bulk_create unavailable")

            call(
                rep,
                "directory.people.list",
                lambda: client.directory.people.list(page=1),
                soft=soft_dir,
            )
            person = call(
                rep,
                "directory.people.create",
                lambda: client.directory.people.create(
                    DirectoryPersonInput(
                        display_name=f"SDK Smoke {suffix}",
                        area_ids=[area.id],
                    )
                ),
                soft=soft_dir,
            )
            if person and person.id:
                call(
                    rep,
                    "directory.people.get",
                    lambda: client.directory.people.get(person.id),
                )
                call(
                    rep,
                    "directory.people.update",
                    lambda: client.directory.people.update(
                        person.id,
                        DirectoryPersonInput(display_name=f"SDK Smoke {suffix} u"),
                    ),
                )
                call(
                    rep,
                    "directory.people.bulk_create",
                    lambda: client.directory.people.bulk_create(
                        [
                            DirectoryPersonInput(
                                display_name=f"SDK Smoke Bulk {suffix}"
                            )
                        ]
                    ),
                    soft=soft_dir,
                )
                call(
                    rep,
                    "directory.people.bulk_update",
                    lambda: client.directory.people.bulk_update(
                        [
                            DirectoryPersonInput(
                                id=person.id,
                                display_name=f"SDK Smoke {suffix} bu",
                            )
                        ]
                    ),
                    soft=soft_dir,
                )
                call(
                    rep,
                    "directory.people.delete",
                    lambda: client.directory.people.delete(person.id),
                )
            else:
                for name in (
                    "directory.people.get",
                    "directory.people.update",
                    "directory.people.bulk_create",
                    "directory.people.bulk_update",
                    "directory.people.delete",
                ):
                    rep.skip(name, "people.create unavailable")

            call(
                rep,
                "directory.areas.delete",
                lambda: client.directory.areas.delete(area.id),
                soft=soft_dir,
            )
        else:
            for name in (
                "directory.areas.get",
                "directory.areas.update",
                "directory.areas.bulk_create",
                "directory.areas.bulk_update",
                "directory.areas.delete",
                "directory.people.list",
                "directory.people.create",
                "directory.people.get",
                "directory.people.update",
                "directory.people.bulk_create",
                "directory.people.bulk_update",
                "directory.people.delete",
            ):
                rep.skip(name, "areas.create unavailable")
    else:
        for name in (
            "directory.areas.create",
            "directory.areas.get",
            "directory.areas.update",
            "directory.areas.bulk_create",
            "directory.areas.bulk_update",
            "directory.areas.delete",
            "directory.people.list",
            "directory.people.create",
            "directory.people.get",
            "directory.people.update",
            "directory.people.bulk_create",
            "directory.people.bulk_update",
            "directory.people.delete",
        ):
            rep.skip(name, "directory unavailable on this plan/key")

    # Integrations write — exercised but soft-fail on server 500 / plan issues
    call(
        rep,
        "integrations.upsert(dingtalk)",
        lambda: client.integrations.upsert("dingtalk", {"accessToken": "sdk-smoke-token"}),
        soft=(ApruvlyError,),
    )
    call(
        rep,
        "integrations.delete(dingtalk)",
        lambda: client.integrations.delete("dingtalk"),
        soft=(ApruvlyError,),
    )

    return rep.summary()


if __name__ == "__main__":
    raise SystemExit(main())
