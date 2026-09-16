"""FastMCP server entry point for the Shlink MCP server."""

from __future__ import annotations

import atexit

from mcp_shlink.config import cached_settings
from mcp_shlink.observability import configure_logging, get_logger, snapshot_metrics
from mcp_shlink.tools import mcp  # noqa: F401  (re-exported for `mcp dev`)


def _init_error_tracking() -> None:
    """Opt-in Sentry initialization via SENTRY_DSN; silent when unset.

    Sentry captures full stack traces with environment context so production
    errors can be traced back to the failing tool call.
    """
    try:
        settings = cached_settings()
    except Exception:
        # Server not configured yet (e.g., tools/list before env vars set).
        return
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.shlink_env,
            traces_sample_rate=0.0,  # error tracking only; no performance spans
        )
        get_logger(settings.shlink_env).info("sentry.initialized", environment=settings.shlink_env)
    except Exception as exc:
        get_logger(settings.shlink_env).warning("sentry.init_failed", error_type=type(exc).__name__)


def _log_shutdown_metrics() -> None:
    """Dump final metrics on shutdown so process lifetime stats are not lost."""
    try:
        settings = cached_settings()
        get_logger(settings.shlink_env).info("server.shutdown", metrics=snapshot_metrics())
    except Exception:
        return


def run() -> None:
    """Run the MCP server over stdio."""
    _init_error_tracking()
    settings = cached_settings()
    configure_logging(settings.shlink_env)
    atexit.register(_log_shutdown_metrics)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run()
