# Apruvly Python Client

Official **stdlib-only** Python client for the [Apruvly](https://apruvly.io) approval workflow API.

Source: [github.com/apruvly/apruvly-python](https://github.com/apruvly/apruvly-python).

- **Zero runtime dependencies** — uses only the Python standard library (`urllib`, `json`, `dataclasses`, `hmac`, …) for a smaller and more auditable supply chain.
- **Resource-oriented API** — `client.workflows`, `client.decisions`, `client.billing`, `client.integrations`, `client.directory`.
- **Typed models** — dataclasses aligned with OpenAPI 1.1.0 (including mixed camelCase / snake_case payloads).
- **Webhook helpers** — verify `notify_url` signatures with constant-time HMAC comparison.

Requires **Python 3.10+**.

## Install

```bash
pip install apruvly
```

From a local checkout:

```bash
pip install -e .
```

## Quickstart

Create an API key in the Apruvly dashboard under **Settings → API Keys**. Keys look like `wf-` followed by 64 alphanumeric characters.

```python
from apruvly import Client
from apruvly.models import WorkflowConfig, WorkflowObject, email_step

client = Client(api_key="wf-...")

# Point at another environment (local / staging):
client = Client(api_key="wf-...", base_url="http://localhost:1509")

# Or configure via environment variables (also used when args are omitted):
#   export APRUVLY_API_KEY=wf-...
#   export APRUVLY_BASE_URL=http://localhost:1509
client = Client()

# Other constructor knobs: timeout=30, accept_language="en"

# Conservative throttle + retry are on by default (see below).

created = client.workflows.create(
    WorkflowConfig(
        object=WorkflowObject(title="Q1 Marketing Budget"),
        expires="24h",
        start="manager",
        workflow={
            "manager": email_step(
                to=["manager@example.com"],
                subject="Please approve",
                body="Approve: ${approve_link}\nReject: ${reject_link}",
            )
        },
    )
)

status = client.workflows.get(created.id)
print(status.status, status.currentStep)
```

You can also pass a plain `dict` for workflow payloads (useful when reading JSON from disk or building channel-specific steps dynamically).

## Authentication & scopes

Every request (except that health needs any valid key) requires a Bearer token:

```http
Authorization: Bearer wf-...
```

| Scope | Operations |
|-------|------------|
| *(none beyond auth)* | `GET /api/v1/health` |
| `api:workflow:write` | create, validate, approve, reject |
| `api:workflow:read` | get by id / external id |
| `api:workflow:list` | search, recent |
| `api:workflow:cancel` | cancel |
| `api:settings:read` | billing, list/get integrations |
| `api:settings:write` | upsert/delete integrations |
| `api:directory:list` | list areas / people |
| `api:directory:read` | get area / person |
| `api:directory:write` | create / update |
| `api:directory:bulk` | bulk create / update |
| `api:directory:delete` | delete |

Missing scope → `ForbiddenError` (HTTP 403).

## Client surface

```python
client.health()

client.workflows.create(config)
client.workflows.validate(config)
client.workflows.get(workflow_id)
client.workflows.get_by_external_id(external_id)
client.workflows.cancel(workflow_id)
client.workflows.cancel_by_external_id(external_id)
client.workflows.search(query=..., status=..., limit=...)
client.workflows.recent()

client.decisions.approve(workflow_id, challenge, comment="LGTM")
client.decisions.reject(workflow_id, challenge, comment="Needs changes")

client.billing.get()

client.integrations.list()
client.integrations.get("slack")
client.integrations.upsert("slack", {"botToken": "...", "signingSecret": "..."})
client.integrations.delete("slack")

client.directory.areas.list() / .create() / .get() / .update() / .delete()
client.directory.areas.bulk_create(...) / .bulk_update(...)
client.directory.people.list(page=1, q="Ada") / .create() / ...
```

Successful calls return the unwrapped `data` field from the API envelope `{ success, message, data }`. HTTP **204** endpoints return `None`.

## Throttle, retry, and backoff

By default the client is **conservative**:

| Setting | Default | Meaning |
|---------|---------|---------|
| `min_interval` | `0.2` s | Minimum spacing between request starts (client-side throttle) |
| `max_retries` | `2` | Extra attempts after the first (up to 3 total) |
| `backoff_factor` | `1.0` s | Exponential base (`1s`, `2s`, `4s`, …) |
| `backoff_max` | `30` s | Cap for backoff / `Retry-After` |
| `jitter` | `true` | Full jitter on sleep delays |

Retries apply to HTTP **429 / 502 / 503 / 504**. Transport errors (connection drops) are retried only for safer methods (`GET`, `PUT`, `DELETE`, …) — **not** `POST` by default, to avoid duplicate workflow creates. On **429**, a `Retry-After` header (seconds) is honored when present.

```python
from apruvly import Client, RetryConfig

# Explicit policy
client = Client(
    api_key="wf-...",
    retry=RetryConfig(min_interval=0.5, max_retries=3, backoff_factor=1.0),
)

# Or individual overrides
client = Client(api_key="wf-...", min_interval=0.5, max_retries=1)

# Disable (e.g. tight unit tests)
client = Client(api_key="wf-...", retry=RetryConfig.disabled())
```

Environment overlays (used when `retry=` is omitted):

```bash
export APRUVLY_MIN_INTERVAL=0.2
export APRUVLY_MAX_RETRIES=2
export APRUVLY_BACKOFF_FACTOR=1.0
export APRUVLY_BACKOFF_MAX=30
export APRUVLY_RETRY_JITTER=true
```

## Errors

```python
from apruvly import (
    AuthError,
    ForbiddenError,
    NotFoundError,
    PaymentRequiredError,
    QuotaExceededError,
    ValidationError,
)

try:
    client.workflows.create(config)
except QuotaExceededError as exc:
    print(exc.quota_type, exc.limit)
except PaymentRequiredError:
    print("Top up credits or upgrade plan")
except ValidationError as exc:
    print(exc.field, exc.message)
```

| Exception | Typical HTTP |
|-----------|--------------|
| `AuthError` | 401 |
| `ForbiddenError` | 403 |
| `NotFoundError` | 404 |
| `PaymentRequiredError` | 402 |
| `ValidationError` | 400, 422 |
| `ConflictError` | 409 |
| `NotAcceptableError` | 406 |
| `QuotaExceededError` | 429 |
| `APIError` | other / transport |

All inherit from `ApruvlyError` and expose `status_code`, `message`, `error_code`, and `data`.

## Webhook signature verification

When an API key has a `notify_url`, Apruvly POSTs a signed payload on terminal workflow events:

```http
Apruvly-Signature: t=<unix>,v1=<hmac_sha256(secret, "<unix>.<raw_body>")>
```

```python
from apruvly import verify_notify_signature, SignatureVerificationError

try:
    verify_notify_signature(
        request_body_bytes,
        request.headers.get("Apruvly-Signature"),
        webhook_secret,
        tolerance=300,  # seconds
    )
except SignatureVerificationError:
    # reject the request
    ...
```

## Examples

| Script | Description |
|--------|-------------|
| [`examples/create_workflow.py`](examples/create_workflow.py) | Validate + create an email approval |
| [`examples/search.py`](examples/search.py) | List recent workflows and billing balance |
| [`examples/verify_webhook.py`](examples/verify_webhook.py) | Sign and verify a sample notify payload |

```bash
export APRUVLY_API_KEY=wf-...
python examples/create_workflow.py
```

## Design notes

- **No third-party HTTP stack** — easier to vendor, audit, and deploy in locked-down environments.
- **Sync-only** — matches `urllib` and keeps the client small.
- **Forward-compatible workflow payloads** — prefer typed builders (`email_step`, `webhook_action`, …) when convenient; fall back to dicts for new channel fields.
- Contract snapshot: [`docs/openapi.json`](docs/openapi.json) (Apruvly API v1.1.0).

## Development

```bash
pip install -e ".[dev]"
ruff check src tests examples
mypy src
pytest
```

Security: see [SECURITY.md](SECURITY.md).

## License

MIT — see [LICENSE](LICENSE).
