"""Helpers for verifying Apruvly outbound notify_url webhooks."""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Mapping


class SignatureVerificationError(ValueError):
    """Raised when an ``Apruvly-Signature`` header fails verification."""


def verify_notify_signature(
    payload: bytes | str,
    signature_header: str | None,
    secret: str,
    *,
    tolerance: int = 300,
    now: int | None = None,
) -> bool:
    """Verify an API-key ``notify_url`` callback signature.

    Apruvly signs terminal workflow events with:

    ``Apruvly-Signature: t=<unix>,v1=<hmac_sha256(secret, "<unix>.<raw_body>")>``

    Args:
        payload: Raw HTTP body bytes (or UTF-8 string) exactly as received.
        signature_header: Value of the ``Apruvly-Signature`` header.
        secret: Webhook signing secret configured on the API key.
        tolerance: Maximum allowed clock skew in seconds (default 5 minutes).
        now: Optional unix timestamp override (for tests).

    Returns:
        ``True`` when the signature is valid.

    Raises:
        SignatureVerificationError: Missing header, bad format, expired
            timestamp, or mismatched signature.
    """
    if not signature_header:
        raise SignatureVerificationError("Missing Apruvly-Signature header")
    if not secret:
        raise SignatureVerificationError("Webhook secret is required")

    timestamp: str | None = None
    signatures: list[str] = []
    for part in signature_header.split(","):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key == "t":
            timestamp = value
        elif key == "v1":
            signatures.append(value)

    if timestamp is None or not signatures:
        raise SignatureVerificationError(
            "Invalid Apruvly-Signature header format; expected t=…,v1=…"
        )

    try:
        ts = int(timestamp)
    except ValueError as exc:
        raise SignatureVerificationError("Invalid timestamp in signature header") from exc

    current = int(time.time() if now is None else now)
    if abs(current - ts) > tolerance:
        raise SignatureVerificationError(
            f"Timestamp outside tolerance ({tolerance}s): t={ts}, now={current}"
        )

    body = payload.encode("utf-8") if isinstance(payload, str) else payload
    signed_payload = f"{timestamp}.".encode() + body
    expected = hmac.new(
        secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()

    if not any(hmac.compare_digest(expected, candidate) for candidate in signatures):
        raise SignatureVerificationError("Signature mismatch")

    return True


def parse_signature_header(header: str) -> tuple[int, list[str]]:
    """Parse ``Apruvly-Signature`` into ``(timestamp, [v1, …])``."""
    timestamp: int | None = None
    signatures: list[str] = []
    for part in header.split(","):
        part = part.strip()
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key == "t":
            timestamp = int(value)
        elif key == "v1":
            signatures.append(value)
    if timestamp is None:
        raise SignatureVerificationError("Missing timestamp in signature header")
    return timestamp, signatures


def extract_signature_header(headers: Mapping[str, str]) -> str | None:
    """Find ``Apruvly-Signature`` in a case-insensitive header map."""
    for key, value in headers.items():
        if key.lower() == "apruvly-signature":
            return value
    return None
