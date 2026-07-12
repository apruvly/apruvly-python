"""Workflow request and response models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from apruvly.models.common import from_mapping, to_dict


@dataclass
class WorkflowObject:
    """Subject of an approval workflow."""

    title: str
    description: str | None = None
    links: list[str] | None = None
    tags: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)


@dataclass
class Action:
    """Lifecycle or step action (webhook, email, channel notify, …)."""

    type: str
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)


@dataclass
class Escalation:
    """Escalation level when a step receives no decision in time."""

    type: str
    data: dict[str, Any]
    after: str
    escalation: Escalation | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> Escalation | None:
        if not data:
            return None
        nested = data.get("escalation")
        return cls(
            type=str(data["type"]),
            data=dict(data.get("data") or {}),
            after=str(data["after"]),
            escalation=cls.from_dict(nested) if isinstance(nested, Mapping) else None,
        )


@dataclass
class StepActions:
    """Actions fired when a step is approved or rejected."""

    approved: list[Action] | None = None
    rejected: list[Action] | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> StepActions | None:
        if not data:
            return None
        return cls(
            approved=_actions(data.get("approved")),
            rejected=_actions(data.get("rejected")),
        )


@dataclass
class Step:
    """A single approval step in a workflow graph."""

    type: str
    data: dict[str, Any]
    minApprovals: int | None = None
    minRejections: int | None = None
    approved: str | None = None
    rejected: str | None = None
    escalation: Escalation | None = None
    actions: StepActions | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Step:
        esc = data.get("escalation")
        acts = data.get("actions")
        return cls(
            type=str(data["type"]),
            data=dict(data.get("data") or {}),
            minApprovals=data.get("minApprovals"),
            minRejections=data.get("minRejections"),
            approved=data.get("approved"),
            rejected=data.get("rejected"),
            escalation=Escalation.from_dict(esc) if isinstance(esc, Mapping) else None,
            actions=StepActions.from_dict(acts) if isinstance(acts, Mapping) else None,
        )


@dataclass
class WorkflowConfig:
    """Payload for create / validate workflow.

    ``workflow`` maps step id → :class:`Step`. Lifecycle hooks go in ``on``.
    """

    object: WorkflowObject
    expires: str
    start: str
    workflow: dict[str, Step]
    on: dict[str, list[Action]] | None = None
    external_id: str | None = None
    disable_email_fallback: bool | None = None
    debug: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "object": to_dict(self.object),
            "expires": self.expires,
            "start": self.start,
            "workflow": {k: to_dict(v) for k, v in self.workflow.items()},
        }
        if self.on is not None:
            payload["on"] = {k: [to_dict(a) for a in v] for k, v in self.on.items()}
        if self.external_id is not None:
            payload["external_id"] = self.external_id
        if self.disable_email_fallback is not None:
            payload["disable_email_fallback"] = self.disable_email_fallback
        if self.debug is not None:
            payload["debug"] = self.debug
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> WorkflowConfig:
        obj = data["object"]
        workflow_raw = data.get("workflow") or {}
        on_raw = data.get("on")
        on: dict[str, list[Action]] | None = None
        if isinstance(on_raw, Mapping):
            on = {str(k): _actions(v) or [] for k, v in on_raw.items()}
        return cls(
            object=WorkflowObject(
                title=str(obj["title"]),
                description=obj.get("description"),
                links=list(obj["links"]) if obj.get("links") else None,
                tags=list(obj["tags"]) if obj.get("tags") else None,
            ),
            expires=str(data["expires"]),
            start=str(data["start"]),
            workflow={
                str(k): Step.from_dict(v) if isinstance(v, Mapping) else v
                for k, v in workflow_raw.items()
            },
            on=on,
            external_id=data.get("external_id"),
            disable_email_fallback=data.get("disable_email_fallback"),
            debug=data.get("debug"),
        )


@dataclass
class WorkflowCreated:
    """Response from ``POST /api/v1/workflow`` (HTTP 202)."""

    id: str
    externalId: str | None = None
    debug: bool | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> WorkflowCreated:
        return from_mapping(cls, data)  # type: ignore[return-value]


@dataclass
class Decision:
    """Recorded decision on a workflow challenge."""

    user: str | None = None
    is_approved: bool | None = None
    ip: str | None = None
    headers: dict[str, Any] | None = None
    data: dict[str, Any] | None = None
    decisionAt: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Decision:
        return from_mapping(cls, data)  # type: ignore[return-value]


@dataclass
class Approver:
    """Current approver / challenge state (snake_case fields)."""

    challenge: str | None = None
    is_approved: bool | None = None
    notify_failed: bool | None = None
    notify_attempts: int | None = None
    notify_retry_at: str | None = None
    notify_last_error: str | None = None
    notify_last_error_detail: str | None = None
    notify_terminal: bool | None = None
    step_name: str | None = None
    esc_level: int | None = None
    display_name: str | None = None
    directory_email: str | None = None
    directory_person_id: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Approver:
        return from_mapping(cls, data)  # type: ignore[return-value]


@dataclass
class WorkflowStatus:
    """Full workflow status (camelCase fields from GET by id)."""

    id: str | None = None
    externalId: str | None = None
    status: str | None = None
    currentStep: str | None = None
    createdAt: str | None = None
    expiresAt: str | None = None
    decisions: list[Decision] = field(default_factory=list)
    currentApprovers: dict[str, Approver] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> WorkflowStatus:
        decisions_raw = data.get("decisions") or []
        approvers_raw = data.get("currentApprovers") or {}
        return cls(
            id=data.get("id"),
            externalId=data.get("externalId"),
            status=data.get("status"),
            currentStep=data.get("currentStep"),
            createdAt=data.get("createdAt"),
            expiresAt=data.get("expiresAt"),
            decisions=[
                Decision.from_dict(d) for d in decisions_raw if isinstance(d, Mapping)
            ],
            currentApprovers={
                str(k): Approver.from_dict(v)
                for k, v in approvers_raw.items()
                if isinstance(v, Mapping)
            },
        )


@dataclass
class WorkflowState:
    """Compact workflow row from search / recent (snake_case)."""

    id: str | None = None
    title: str | None = None
    current_step: str | None = None
    current_status: str | None = None
    error_message: str | None = None
    external_id: str | None = None
    created_at: str | None = None
    expires_at: str | None = None
    completed_at: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> WorkflowState:
        return from_mapping(cls, data)  # type: ignore[return-value]


@dataclass
class DecisionBody:
    """Optional body for approve / reject."""

    comment: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------


def email_step(
    *,
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    html: bool | None = None,
    min_approvals: int | None = None,
    min_rejections: int | None = None,
    approved: str | None = None,
    rejected: str | None = None,
    escalation: Escalation | None = None,
    actions: StepActions | None = None,
) -> Step:
    """Build an email approval step.

    The email ``body`` must include ``${approve_link}`` and ``${reject_link}``.
    """
    data: dict[str, Any] = {"to": list(to), "subject": subject, "body": body}
    if cc is not None:
        data["cc"] = list(cc)
    if bcc is not None:
        data["bcc"] = list(bcc)
    if html is not None:
        data["html"] = html
    return Step(
        type="email",
        data=data,
        minApprovals=min_approvals,
        minRejections=min_rejections,
        approved=approved,
        rejected=rejected,
        escalation=escalation,
        actions=actions,
    )


def slack_step(
    *,
    to: list[str],
    text: str | None = None,
    min_approvals: int | None = None,
    approved: str | None = None,
    rejected: str | None = None,
    escalation: Escalation | None = None,
    actions: StepActions | None = None,
    **extra: Any,
) -> Step:
    """Build a Slack approval step (``to`` may be emails or ``#channel`` ids)."""
    data: dict[str, Any] = {"to": list(to), **extra}
    if text is not None:
        data["text"] = text
    return Step(
        type="slack",
        data=data,
        minApprovals=min_approvals,
        approved=approved,
        rejected=rejected,
        escalation=escalation,
        actions=actions,
    )


def webhook_action(
    *,
    url: str,
    method: str = "POST",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: str | None = None,
    async_: bool | None = None,
) -> Action:
    """Build a webhook lifecycle / step action."""
    data: dict[str, Any] = {"url": url, "method": method}
    if headers is not None:
        data["headers"] = headers
    if body is not None:
        data["body"] = body
    if timeout is not None:
        data["timeout"] = timeout
    if async_ is not None:
        data["async"] = async_
    return Action(type="webhook", data=data)


def _actions(value: Any) -> list[Action] | None:
    if not value:
        return None
    result: list[Action] = []
    for item in value:
        if isinstance(item, Action):
            result.append(item)
        elif isinstance(item, Mapping):
            result.append(Action(type=str(item["type"]), data=dict(item.get("data") or {})))
    return result


def as_workflow_payload(config: WorkflowConfig | Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a workflow create/validate payload to a plain dict."""
    if isinstance(config, WorkflowConfig):
        return config.to_dict()
    return dict(config)
