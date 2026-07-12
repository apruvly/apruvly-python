"""Integration models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from apruvly.models.common import to_dict


@dataclass
class IntegrationStatus:
    """GET response for an integration (secrets never returned)."""

    integration: str
    configured: bool
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> IntegrationStatus:
        known = {"integration", "configured"}
        extras = {k: v for k, v in data.items() if k not in known}
        return cls(
            integration=str(data["integration"]),
            configured=bool(data["configured"]),
            extras=extras,
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Read an extra non-secret field (e.g. ``hasBotToken``)."""
        return self.extras.get(key, default)


@dataclass
class MSTeamsIntegrationConfig:
    tenantId: str
    botAppId: str
    botAppPassword: str

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)


@dataclass
class SlackIntegrationConfig:
    botToken: str
    signingSecret: str

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)


@dataclass
class WhatsAppIntegrationConfig:
    phoneNumberId: str
    accessToken: str
    verifyToken: str

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)


@dataclass
class TelegramIntegrationConfig:
    botToken: str

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)


@dataclass
class DingTalkIntegrationConfig:
    accessToken: str

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)


@dataclass
class DiscordIntegrationConfig:
    applicationId: str
    botToken: str
    publicKey: str

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)


@dataclass
class SMTPIntegrationConfig:
    host: str
    port: int
    from_: str  # maps to JSON "from"
    username: str | None = None
    password: str | None = None
    useTLS: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = to_dict(self)
        if "from_" in payload:
            payload["from"] = payload.pop("from_")
        return payload


@dataclass
class TwilioIntegrationConfig:
    accountSid: str
    authToken: str | None = None
    apiKeySid: str | None = None
    apiKeySecret: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)


@dataclass
class TwilioWhatsAppIntegrationConfig:
    accountSid: str
    fromPhone: str
    authToken: str | None = None
    apiKeySid: str | None = None
    apiKeySecret: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)


IntegrationConfig = (
    MSTeamsIntegrationConfig
    | SlackIntegrationConfig
    | WhatsAppIntegrationConfig
    | TelegramIntegrationConfig
    | DingTalkIntegrationConfig
    | DiscordIntegrationConfig
    | SMTPIntegrationConfig
    | TwilioIntegrationConfig
    | TwilioWhatsAppIntegrationConfig
    | Mapping[str, Any]
)


def as_integration_payload(config: IntegrationConfig) -> dict[str, Any]:
    if isinstance(config, Mapping):
        return dict(config)
    return config.to_dict()
