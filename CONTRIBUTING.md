# Contributing

## Local setup

```bash
pip install -e ".[dev]"
git config core.hooksPath .githooks
ruff check src tests examples
mypy src
pytest
```

The pre-commit hook runs ruff, mypy, and pytest before each commit.

## Issues

Use the issue templates when opening bugs or feature requests.  
Security reports must follow [SECURITY.md](SECURITY.md) — never file them as public issues.

## Releases

Keep the version in sync in:

- `pyproject.toml` (`project.version`)
- `src/apruvly/_version.py` (`__version__`)

Tag and push to publish via [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC):

```bash
git tag -a v0.1.0 -m "apruvly 0.1.0"
git push origin v0.1.0
```

That runs [`.github/workflows/publish.yml`](.github/workflows/publish.yml).

### One-time Trusted Publishing setup

**GitHub**

1. Repo **Settings → Environments → New environment** named exactly `pypi`.
2. Recommended: restrict deployments to tags matching `v*` (and/or require reviewers).
3. Enable **Private vulnerability reporting** under **Settings → Code security**.

**PyPI** (project does not exist yet → pending publisher)

1. Sign in at [pypi.org](https://pypi.org) → **Your account → Publishing**.
2. Under **GitHub**, fill in:
   - **PyPI Project Name:** `apruvly`
   - **Owner:** `apruvly`
   - **Repository name:** `apruvly-python`
   - **Workflow name:** `publish.yml`
   - **Environment name:** `pypi`
3. Click **Add**.

If the project already exists on PyPI: open the project → **Publishing** and add the same GitHub publisher (without the project name field).

Do not store a long-lived `PYPI_API_TOKEN` for this flow — OIDC mints a short-lived token per run.
