#!/usr/bin/env python3
"""Verify an Apruvly notify_url webhook signature.

Usage:
    python examples/verify_webhook.py
"""

from __future__ import annotations

import hashlib
import hmac
import time

from apruvly import SignatureVerificationError, verify_notify_signature


def main() -> None:
    secret = "whsec_example_secret"
    body = b'{"event":"workflow_approved","workflow_id":"11111111-1111-1111-1111-111111111111","status":"approved"}'
    timestamp = int(time.time())
    digest = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}.".encode() + body,
        hashlib.sha256,
    ).hexdigest()
    header = f"t={timestamp},v1={digest}"

    ok = verify_notify_signature(body, header, secret)
    print("valid signature:" if ok else "invalid:", ok)

    try:
        verify_notify_signature(body, "t=1,v1=deadbeef", secret, tolerance=300)
    except SignatureVerificationError as exc:
        print("rejected forged signature:", exc)


if __name__ == "__main__":
    main()
