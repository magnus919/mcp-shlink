---
name: shlink-server
description: Build, test, and run the mcp-shlink MCP server (Python, FastMCP, strict mypy, coverage-gated tests).
---

# mcp-shlink agent guide

## Setup

```bash
pip install -e ".[dev]"
pre-commit install
```

## Verify everything (same gates as CI)

```bash
ruff check . && ruff format . --check && mypy src/ && pytest
```

Additional quality gates (all also run in CI):

```bash
vulture src              # dead code
xenon src --max-absolute B --max-average A --max-modules B   # complexity
deptry src               # unused dependencies
python scripts/check_file_size.py            # large-file guard
python scripts/check_agents_md.py            # AGENTS.md freshness
python scripts/generate_architecture_diagram.py --check   # docs must match code
```

## Tests

- `pytest` runs unit + integration tests with `-n auto` (xdist), random order,
  and an 80% coverage gate.
- Integration tests start a local Shlink stub (`tests/shlink_stub_server.py`)
  on an ephemeral port; no real Shlink instance is ever needed.
- Keep tests isolated: no ordering dependence, no real network, no real
  credentials (enforced by `tests/conftest.py`).

## Local interactive QA

```bash
# 1. Start the stub Shlink API (terminal 1)
SHLINK_API_KEY=changeme python -m tests.shlink_stub_server --port 8765

# 2. Run the MCP server against it (terminal 2)
SHLINK_BASE_URL=http://127.0.0.1:8765 SHLINK_API_KEY=changeme python -m mcp_shlink.server
```

Then connect with MCP Inspector: `SHLINK_BASE_URL=http://127.0.0.1:8765
SHLINK_API_KEY=changeme uv run mcp dev src/mcp_shlink/server.py` and
invoke tools (all five are safe against the stub: create/list/get/delete URLs,
list tags).

## Conventions

- Strict typing everywhere: `mypy src/` must stay clean.
- Every tool runs inside `observability.traced()`; never log URLs, tags, slugs,
  or credentials (logger redacts, but do not rely on it).
- Env access only through `mcp_shlink.config.load_settings()`.
- Ship risky behavior behind a flag in `mcp_shlink.features.FLAG_DEFAULTS`
  (default OFF) with a removal plan documented in the comment above it.
- TODO/FIXME comments must end with an owner reference, e.g. `TODO(magnus): ...`.
- Update `AGENTS.md` when commands, env vars, or workflow files change;
  `scripts/check_agents_md.py` enforces this in CI and pre-commit.
