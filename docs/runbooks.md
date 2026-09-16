# Runbook: mcp-shlink Operations

Incident response procedures for the Shlink MCP server. This is the local,
repository-owned playbook; link additional external pages here as they exist.

## Where things live

| What | Where |
|------|-------|
| CI failure alerts | GitHub Issues labeled `ci-failure` (created by `.github/workflows/alert-on-failure.yml`) |
| PyPI publish status | GitHub Actions > "Publish to PyPI" + https://pypi.org/p/mcp-shlink |
| Structured logs | Server stderr (JSON lines; `trace_id`, `request_id`, `environment` per line) |
| Runtime metrics | `get_metrics` MCP tool or `snapshot_metrics()` (per-tool calls, errors, p95 latency) |

## Incident: tool calls fail with 5xx / connection errors

1. Confirm scope: run `get_metrics`; check `tool.*.errors` counters.
2. Read stderr logs for `tool.failed` events; each carries `error_type` and
   `trace_id` for correlation.
3. Verify the Shlink instance is up (`GET {SHLINK_BASE_URL}/rest/health`).
4. If transient upstream flakiness: enable `FLAG_SHLINK_RETRY_5XX_ENABLED=true`
   for the affected deployment to activate client retry with backoff.
5. If persistent: it is the Shlink instance, not this server. Escalate to the
   Shlink operator.

## Incident: a release broke users on PyPI

1. Identify the bad version from GitHub Releases ("Release Notes" workflow adds
   a changelog per tag).
2. Roll back by re-publishing the previous tag: the previous version remains
   installable, so pin users to it (`pip install mcp-shlink==<good-version>`).
3. Open an issue with the `ci-failure` label linking the failing run.
4. Post-mortem: note the root cause in the issue; add a regression test.

## Incident: suspected leaked API key

1. Rotate the key in Shlink (`shlink api-key:generate`).
2. Search history: `git log -S '<key-prefix>'` to check for committed secrets.
3. The repo runs gitleaks in CI and detect-secrets pre-commit; both must be
   clean before the rotation can be closed out.
4. If a key reached logs: the logger redacts `X-Api-Key`/`authorization` and
   key-shaped fields, but assume exposure and rotate anyway.

## Health snapshot (no external monitoring stack required)

- Process alive: stdio transport connected (MCP host will surface transport
  errors).
- Per-tool error rate: `get_metrics` counters.
- Latency: `get_metrics` `durations_ms` (mean/p95/max per tool).

When this project gains production dashboards, link them in this table.
