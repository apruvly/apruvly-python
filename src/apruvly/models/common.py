"""Shared model helpers and enums."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, fields, is_dataclass
from enum import Enum
from typing import Any, TypeVar, cast

T = TypeVar("T")


class WorkflowStatusValue(str, Enum):
    """Terminal and in-flight workflow statuses."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELED = "canceled"
    EXPIRED = "expired"
    ERROR = "error"


class IntegrationName(str, Enum):
    """Supported notification integrations."""

    MS_TEAMS = "ms-teams"
    SLACK = "slack"
    WHATSAPP = "whatsapp"
    SMTP = "smtp"
    TELEGRAM = "telegram"
    DINGTALK = "dingtalk"
    TWILIO = "twilio"
    TWILIO_WHATSAPP = "twilio-whatsapp"
    DISCORD = "discord"


class StepType(str, Enum):
    """Channel types for approval steps."""

    EMAIL = "email"
    MS_TEAMS = "ms-teams"
    SLACK = "slack"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    DINGTALK = "dingtalk"
    DISCORD = "discord"
    TWILIO_SMS = "twilio-sms"
    TWILIO_WHATSAPP = "twilio-whatsapp"


class ContactProvider(str, Enum):
    """Directory contact providers."""

    EMAIL = "email"
    SLACK = "slack"
    MS_TEAMS = "ms-teams"
    TWILIO_SMS = "twilio-sms"
    TWILIO_WHATSAPP = "twilio-whatsapp"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    DISCORD = "discord"


def to_dict(value: Any, *, omit_none: bool = True) -> Any:
    """Convert dataclasses / enums / mappings into JSON-serializable structures."""
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        result: dict[str, Any] = {}
        for f in fields(value):
            item = getattr(value, f.name)
            if omit_none and item is None:
                continue
            result[f.name] = to_dict(item, omit_none=omit_none)
        return result
    if isinstance(value, Mapping):
        return {
            str(k): to_dict(v, omit_none=omit_none)
            for k, v in value.items()
            if not (omit_none and v is None)
        }
    if isinstance(value, (list, tuple)):
        return [to_dict(v, omit_none=omit_none) for v in value]
    return value


def from_mapping(cls: type[T], data: Mapping[str, Any] | None) -> T | None:
    """Instantiate a dataclass from a mapping, ignoring unknown keys."""
    if data is None:
        return None
    if not is_dataclass(cls):
        raise TypeError(f"{cls!r} is not a dataclass")
    known = {f.name for f in fields(cls)}
    kwargs = {k: v for k, v in data.items() if k in known}
    return cls(**kwargs)


def dataclass_asdict(obj: Any) -> dict[str, Any]:
    """``dataclasses.asdict`` wrapper that keeps enum values as strings."""
    raw = asdict(obj)
    return cast(dict[str, Any], to_dict(raw))
