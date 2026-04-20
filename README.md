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

Set these environment variables before running the server:

| Variable | Description | Required |
|----------|-------------|----------|
| `SHLINK_BASE_URL` | Your Shlink instance base URL (e.g., `https://shlink.example.com`) | Yes |
| `SHLINK_API_KEY` | Your Shlink API key | Yes |

Generate an API key in Shlink:

```bash
shlink api-key:generate --name=my_api_key
```

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

## Development

```bash
# Clone the repository
git clone https://github.com/magnus919/mcp-shlink
cd mcp-shlink

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Lint and format
ruff check .
ruff format .

# Type check
mypy src/

# Full verification
ruff check . && ruff format . --check && mypy src/ && pytest
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

## License

Apache 2.0. See [LICENSE](LICENSE).
