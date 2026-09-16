# Architecture & Service Dependencies

The diagram below is **generated** from the live MCP tool registry by
`scripts/generate_architecture_diagram.py` and verified in CI
(`generate_architecture_diagram.py --check`), so it cannot drift from the code.

```mermaid
flowchart LR
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
    TOOLS -- "create_short_url" --> CLIENT
    TOOLS -- "delete_short_url" --> CLIENT
    TOOLS -- "get_metrics" --> CLIENT
    TOOLS -- "get_short_url" --> CLIENT
    TOOLS -- "list_short_urls" --> CLIENT
    TOOLS -- "list_tags" --> CLIENT
    CLIENT --> RETRY
    RETRY -- "HTTP (X-Api-Key)" --> SHLINK
    TOOLS -.-> OBS
    TOOLS -.-> FLAGS
```

## External service dependencies

| Dependency | Protocol | Auth | Failure handling |
|------------|----------|------|------------------|
| Shlink REST v3 | HTTPS (JSON) | `X-Api-Key` header | 5xx/connection errors retried with exponential backoff behind `shlink.retry_5xx.enabled`; 4xx surfaced as `httpx.HTTPStatusError` |

There are no databases, queues, or other external services. Configuration and
optional integrations are listed in the README (Configuration and Error
tracking sections).
