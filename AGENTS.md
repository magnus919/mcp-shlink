# AGENTS.md

## Project Overview

`mcp-shlink` is an MCP (Model Context Protocol) server that exposes Shlink
link shortening service functionality as tools for AI assistants.

- **Repository**: `magnus919/mcp-shlink`
- **Framework**: Python MCP SDK (`mcp` package, FastMCP class)
- **Python**: >=3.10

## Developer Commands

```bash
# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run tests (unit + integration, parallel, random order, 80% coverage gate)
pytest

# Lint and format
ruff check .
ruff format .

# Type check
mypy src/

# Full verification (lint -> format -> typecheck -> test)
ruff check . && ruff format . --check && mypy src/ && pytest

# Additional quality gates (also enforced in CI)
vulture src                          # dead code
xenon src --max-absolute B --max-average A --max-modules B   # complexity
deptry src                           # unused dependencies
python scripts/check_file_size.py    # large-file guard (512 KiB)
python scripts/check_agents_md.py    # validates this file stays current
python scripts/generate_architecture_diagram.py --check       # docs sync
```

## Pre-commit hooks

Quality checks run locally before every commit:

```bash
pre-commit install           # one-time setup
pre-commit run --all-files   # run everything now
```

## Project Structure

```
src/mcp_shlink/
├── server.py          # FastMCP entry point; Sentry opt-in, shutdown metrics
├── client.py          # Shlink API client (retry/backoff behind a flag)
├── tools.py           # MCP tool definitions (traced, logged, measured)
├── models.py          # Pydantic models for API requests/responses
├── config.py          # Typed settings from env (single source of truth)
├── observability.py   # JSON logs, redaction, trace ids, metrics
├── features.py        # Feature flag registry (env-driven, default OFF)
└── analytics.py       # Opt-in anonymous tool usage events

tests/                 # test_*.py; integration tests use a local Shlink stub
scripts/               # CI/pre-commit helper scripts
docs/                  # architecture, runbooks, secrets policy
```

## Shlink API Integration

- **Base URL**: `{SHLINK_BASE_URL}/rest/v3`
- **Auth**: `X-Api-Key: {api_key}` header
- **Endpoints used**:
  - `POST /short-urls` - Create short URL
  - `GET /short-urls` - List short URLs
  - `GET /short-urls/{shortCode}` - Get URL details
  - `DELETE /short-urls/{shortCode}` - Delete URL
  - `GET /tags` - List tags
- 5xx/connection failures are retried with exponential backoff when
  `shlink.retry_5xx.enabled` is enabled.

## Configuration

Server accepts these environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `SHLINK_BASE_URL` | Shlink instance base URL | Yes |
| `SHLINK_API_KEY` | Shlink API key | Yes |
| `SHLINK_ENV` | Deployment environment name in logs | No |
| `SHLINK_ANALYTICS_ENABLED` | Opt-in anonymous usage events | No |
| `SHLINK_ANALYTICS_ENDPOINT` | HTTP collector for usage events | No |
| `SENTRY_DSN` | Opt-in Sentry error tracking | No |
| `FLAG_*` | Feature flags (see `src/mcp_shlink/features.py`) | No |

## Running the Server

```bash
# With environment variables
SHLINK_BASE_URL=https://shlink.example.com SHLINK_API_KEY=your-key python -m mcp_shlink.server

# Or against the local stub for development (see "Local interactive QA")
SHLINK_API_KEY=changeme python -m tests.shlink_stub_server --port 8765

# Install into Claude Desktop
uv run mcp install src/mcp_shlink/server.py --name "shlink"
```

## Local interactive QA

1. Start the stub: `SHLINK_API_KEY=changeme python -m tests.shlink_stub_server --port 8765`
2. Point the server at it: `SHLINK_BASE_URL=http://127.0.0.1:8765 SHLINK_API_KEY=changeme python -m mcp_shlink.server`
3. Drive tools via MCP Inspector: `SHLINK_BASE_URL=http://127.0.0.1:8765 SHLINK_API_KEY=changeme uv run mcp dev src/mcp_shlink/server.py`

## Conventions

- Strict typing everywhere; `mypy src/` must stay clean.
- Env access only through `mcp_shlink.config.load_settings()`.
- Every tool runs inside `observability.traced()`; never log URLs, tags,
  slugs, or credentials.
- Ship risky behavior behind a flag in `features.FLAG_DEFAULTS` (default OFF).
- `TODO`/`FIXME` comments must carry an owner: `TODO(magnus): ...`.
- Keep tests isolated and parallel-safe (`-n auto`); never hit a real Shlink
  instance.
- Update this file when commands, env vars, or CI jobs change;
  `scripts/check_agents_md.py` fails CI if the docs drift.

## CI/CD

- GitHub Actions run on push/PR: lint → format → typecheck → code quality
  (vulture/xenon/deptry/jscpd) → file-size guard → tests (coverage gate) →
  AGENTS.md validation → gitleaks secret detection → CodeQL → diagram check.
- CI failures automatically open a labeled GitHub issue
  (`.github/workflows/alert-on-failure.yml`).
- Tagging `v*.*.*` generates GitHub release notes and publishes to PyPI via
  Trusted Publishing.
- Dependencies are locked (`uv.lock`, `requirements.txt`) and updated by
  Renovate with a minimum release age (see `renovate.json`).
