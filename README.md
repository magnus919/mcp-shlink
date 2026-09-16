# mcp-shlink

[![PyPI version](https://img.shields.io/pypi/v/mcp-shlink.svg)](https://pypi.org/project/mcp-shlink/)
[![Python versions](https://img.shields.io/pypi/pyversions/mcp-shlink.svg)](https://pypi.org/project/mcp-shlink/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/magnus919/mcp-shlink/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/magnus919/mcp-shlink/actions/workflows/ci.yml)

A Model Context Protocol (MCP) server for [Shlink](https://shlink.io/) link shortening service. This server exposes Shlink's URL shortening, management, and tagging capabilities as MCP tools for AI assistants.

## Features

- Create shortened URLs with custom slugs, tags, and expiration
- List all shortened URLs with pagination info
- Get details of specific URLs by short code
- Delete shortened URLs
- List and manage tags
- Full type safety with Pydantic models
- Built with the official MCP Python SDK

## Requirements

- Python >= 3.10
- A Shlink instance with API access

## Installation

```bash
pip install mcp-shlink
```

## Configuration

Copy `.env.example` to `.env` (gitignored) or export the variables directly:

| Variable | Description | Required |
|----------|-------------|----------|
| `SHLINK_BASE_URL` | Your Shlink instance base URL (e.g., `https://shlink.example.com`) | Yes |
| `SHLINK_API_KEY` | Your Shlink API key | Yes |
| `SHLINK_ENV` | Environment name shown in logs (default: `production`) | No |
| `SHLINK_ANALYTICS_ENABLED` | Opt-in anonymous tool usage events (default: `false`) | No |
| `SHLINK_ANALYTICS_ENDPOINT` | Optional HTTP collector for usage events | No |
| `SENTRY_DSN` | Opt-in Sentry error tracking (see below) | No |
| `FLAG_*` | Feature flags (see [Features & flags](#features--flags)) | No |

Generate an API key in Shlink:

```bash
shlink api-key:generate --name=my_api_key
```

## Features & flags

Risky behavior ships behind environment-driven feature flags (default OFF):

| Flag | Env override | Purpose |
|------|--------------|---------|
| `shlink.retry_5xx.enabled` | `FLAG_SHLINK_RETRY_5XX_ENABLED=true` | Retry Shlink 5xx/connection errors with exponential backoff |
| `shlink.soft_delete.enabled` | `FLAG_SHLINK_SOFT_DELETE_ENABLED=true` | Stage deletions behind a confirmation step |
| `shlink.analytics.enabled` | `FLAG_SHLINK_ANALYTICS_ENABLED=true` | Anonymous tool usage events |

## Observability

- **Structured logging**: one JSON line per event on stderr, including
  `trace_id`, `request_id`, `environment`, and per-tool `duration_ms`.
  Credentials, tokens, and URLs are redacted automatically.
- **Metrics**: the built-in `get_metrics` tool reports per-tool call counts,
  error counts, and latency (mean/p95/max); metrics are also dumped at shutdown.
- **Error tracking**: set `SENTRY_DSN` to enable Sentry (full stack traces with
  environment context). Install with `pip install "mcp-shlink[error-tracking]"`.

## Documentation

- [Architecture & service dependencies](docs/architecture.md) (generated
  diagram, verified in CI)
- [Runbooks](docs/runbooks.md) (incident response)
- [Secrets management](docs/secrets.md) (policy and enforcement)

## Usage

### Running as a standalone MCP server

```bash
SHLINK_BASE_URL=https://shlink.example.com SHLINK_API_KEY=your-key python -m mcp_shlink.server
```

### Installing into Claude Desktop

```bash
uv run mcp install src/mcp_shlink/server.py --name "shlink"
```

### Running with MCP Inspector

```bash
SHLINK_BASE_URL=https://shlink.example.com SHLINK_API_KEY=your-key uv run mcp dev src/mcp_shlink/server.py
```

## Available Tools

| Tool | Description |
|------|-------------|
| `create_short_url` | Create a new shortened URL |
| `list_short_urls` | List all shortened URLs |
| `get_short_url` | Get details of a URL by short code |
| `delete_short_url` | Delete a shortened URL |
| `list_tags` | List all tags |
| `get_metrics` | Server metrics: per-tool calls, errors, latencies |

## Development

```bash
# Clone the repository
git clone https://github.com/magnus919/mcp-shlink
cd mcp-shlink

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests (unit + integration, parallel, 80% coverage gate)
pytest

# Lint and format
ruff check .
ruff format .

# Type check
mypy src/

# Full verification
ruff check . && ruff format . --check && mypy src/ && pytest
```

Integration tests run against a local Shlink stub (`tests/shlink_stub_server.py`);
no real Shlink instance is needed.

## Local interactive QA

You can exercise the full tool surface without a real Shlink deployment:

```bash
# 1. Start the local Shlink stub API
SHLINK_API_KEY=changeme python -m tests.shlink_stub_server --port 8765

# 2. Drive the MCP server with MCP Inspector against the stub
SHLINK_BASE_URL=http://127.0.0.1:8765 SHLINK_API_KEY=changeme \
  uv run mcp dev src/mcp_shlink/server.py
```

Invoke any of the five tools in the Inspector UI; all are safe against the stub.

## Project Structure

```
src/mcp_shlink/
├── server.py       # FastMCP server entry point
├── client.py       # Shlink API client
├── tools.py        # MCP tool definitions
├── models.py       # Pydantic models for API requests/responses
├── config.py       # Typed settings loaded from environment
├── observability.py  # Structured logs, redaction, trace ids, metrics
├── features.py     # Feature flag registry
└── analytics.py    # Opt-in anonymous usage events

tests/              # Unit + integration tests (local Shlink stub)
scripts/            # CI/pre-commit helper scripts
docs/               # Architecture, runbooks, secrets policy
```

## License

Apache 2.0. See [LICENSE](LICENSE).
