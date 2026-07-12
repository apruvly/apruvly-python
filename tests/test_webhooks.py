"""Webhook signature verification tests."""

from __future__ import annotations

import hashlib
import hmac
import unittest

from apruvly.webhooks import SignatureVerificationError, verify_notify_signature


def _sign(secret: str, timestamp: int, body: bytes) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}.".encode() + body,
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


class WebhookTests(unittest.TestCase):
    def test_valid_signature(self) -> None:
        secret = "whsec_test"
        body = b'{"event":"workflow_approved","workflow_id":"w-1"}'
        ts = 1_700_000_000
        header = _sign(secret, ts, body)
        self.assertTrue(
            verify_notify_signature(body, header, secret, now=ts, tolerance=300)
        )

    def test_bad_signature(self) -> None:
        body = b"{}"
        with self.assertRaises(SignatureVerificationError):
            verify_notify_signature(
                body,
                "t=1700000000,v1=deadbeef",
                "secret",
                now=1_700_000_000,
            )

    def test_expired_timestamp(self) -> None:
        secret = "s"
        body = b"{}"
        ts = 1_700_000_000
        header = _sign(secret, ts, body)
        with self.assertRaises(SignatureVerificationError) as ctx:
            verify_notify_signature(body, header, secret, now=ts + 10_000, tolerance=300)
        self.assertIn("tolerance", str(ctx.exception).lower())

    def test_missing_header(self) -> None:
        with self.assertRaises(SignatureVerificationError):
            verify_notify_signature(b"{}", None, "secret")


if __name__ == "__main__":
    unittest.main()
