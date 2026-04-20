# AGENTS.md

## Project Overview

`mcp-shlink` is an MCP (Model Context Protocol) server that exposes Shlink link shortening service functionality as tools for AI assistants.

- **Repository**: `magnus919/mcp-shlink`
- **Framework**: Python MCP SDK (`mcp` package, FastMCP class)
- **Python**: >=3.10

## Developer Commands

```bash
# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint and format
ruff check .
ruff format .

# Type check
mypy src/

# Full verification (lint -> typecheck -> test)
ruff check . && ruff format . --check && mypy src/ && pytest

# Run MCP server locally (for testing with MCP Inspector)
python -m mcp_shlink.server
# Or with uv:
uv run mcp dev src/mcp_shlink/server.py
```

## Project Structure

```
src/mcp_shlink/
├── server.py       # FastMCP server entry point
├── client.py       # Shlink API client
├── tools.py        # MCP tool definitions
└── models.py       # Pydantic models for API requests/responses

tests/
├── test_tools.py    # Unit tests for MCP tools
└── test_client.py   # Unit tests for Shlink client
```

## Shlink API Integration

- **Base URL**: `https://{domain}/rest/v3`
- **Auth**: `X-Api-Key: {api_key}` header
- **Endpoints used**:
  - `POST /short-urls` - Create short URL
  - `GET /short-urls` - List short URLs
  - `GET /short-urls/{shortCode}` - Get URL details
  - `DELETE /short-urls/{shortCode}` - Delete URL
  - `GET /tags` - List tags

## Configuration

Server accepts these environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `SHLINK_BASE_URL` | Shlink instance base URL | Yes |
| `SHLINK_API_KEY` | Shlink API key | Yes |

## Running the Server

```bash
# With environment variables
SHLINK_BASE_URL=https://shlink.example.com SHLINK_API_KEY=your-key python -m mcp_shlink.server

# Install into Claude Desktop
uv run mcp install src/mcp_shlink/server.py --name "shlink"
```

## CI/CD

- GitHub Actions runs on push/PR: lint (ruff) → typecheck (mypy) → test (pytest)
- Publishing to PyPI is automatic on git tags via Trusted Publishing (no manual tokens)

## Adding New Tools

1. Define tool in `src/mcp_shlink/tools.py` using `@mcp.tool()` decorator
2. Add Pydantic models for request/response in `src/mcp_shlink/models.py`
3. Add tests in `tests/`
4. Update `server.py` imports if needed
