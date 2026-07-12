#!/usr/bin/env python3
"""Search recent workflows.

Usage:
    export APRUVLY_API_KEY=wf-...
    python examples/search.py
"""

from __future__ import annotations

import os
import sys

from apruvly import Client


def main() -> int:
    if not os.environ.get("APRUVLY_API_KEY"):
        print("Set APRUVLY_API_KEY to a wf-… key from the Apruvly dashboard.", file=sys.stderr)
        return 1

    # Reads APRUVLY_API_KEY and optional APRUVLY_BASE_URL from the environment.
    client = Client()
    print(f"Using API {client.base_url}", file=sys.stderr)

    print("Recent workflows:")
    for row in client.workflows.recent():
        print(f"  {row.id}  {row.current_status:10}  {row.title}")

    query = os.environ.get("APRUVLY_SEARCH_QUERY", "")
    if query:
        print(f'\nSearch for "{query}":')
        for row in client.workflows.search(query=query, limit=20):
            print(f"  {row.id}  {row.current_status:10}  {row.title}")

    billing = client.billing.get()
    print(f"\nCredit balance: {billing.balance}")
    if billing.plan:
        print(f"Plan: {billing.plan.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
