#!/usr/bin/env python
"""Generate docs/architecture.mmd from the installed package's tools.

The diagram is derived from the live tool registry (via
``mcp_shlink.tools.mcp``), so it cannot drift from reality. CI runs this with
``--check``: if a committed diagram differs from what the code would produce,
the job fails and docs stay honest.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIAGRAM_PATH = ROOT / "docs" / "architecture.mmd"

HEADER = """flowchart LR
    subgraph Client["AI assistant / MCP client"]
        HOST["MCP host (stdio)"]
    end
    subgraph Server["mcp-shlink server"]
        TOOLS["FastMCP tool registry"]
        CLIENT["ShlinkClient (httpx)"]
        RETRY["Retry + backoff (flag: shlink.retry_5xx.enabled)"]
        OBS["observability: JSON logs, redaction, trace ids, metrics"]
        FLAGS["features: env-driven feature flags"]
    end
    subgraph Upstream["External service"]
        SHLINK["Shlink REST v3 API"]
    end
    HOST -- "initialize / tools-list / tool calls" --> TOOLS
"""


def _build_diagram() -> str:
    """Render the flowchart with one edge per registered MCP tool."""
    from mcp_shlink.tools import mcp  # local import: needs the package installed

    lines = [HEADER]
    tool_names = sorted(tool.name for tool in mcp._tool_manager.list_tools())  # type: ignore[attr-defined]
    for tool_name in tool_names:
        lines.append(f'    TOOLS -- "{tool_name}" --> CLIENT\n')
    lines.append("    CLIENT --> RETRY\n")
    lines.append('    RETRY -- "HTTP (X-Api-Key)" --> SHLINK\n')
    lines.append("    TOOLS -.-> OBS\n")
    lines.append("    TOOLS -.-> FLAGS\n")
    return "".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed diagram matches generated output instead of writing it",
    )
    args = parser.parse_args()

    rendered = _build_diagram()
    if args.check:
        committed = DIAGRAM_PATH.read_text(encoding="utf-8") if DIAGRAM_PATH.exists() else ""
        if committed != rendered:
            print(
                "docs/architecture.mmd is stale. Run "
                "'python scripts/generate_architecture_diagram.py' and commit the result."
            )
            return 1
        print("docs/architecture.mmd is up to date.")
        return 0

    DIAGRAM_PATH.parent.mkdir(parents=True, exist_ok=True)
    DIAGRAM_PATH.write_text(rendered, encoding="utf-8")
    print(f"wrote {DIAGRAM_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
