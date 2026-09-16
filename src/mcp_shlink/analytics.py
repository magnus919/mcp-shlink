"""Opt-in, anonymous tool usage events (product analytics).

Disabled by default. When ``SHLINK_ANALYTICS_ENABLED=true`` (or the
``shlink.analytics.enabled`` feature flag is on) the server fires one event per
tool call containing only the tool name, outcome, duration bucket, and
environment name. No URLs, tags, slugs, or credentials are ever included, and
failures are swallowed so analytics can never break tool execution.
"""

from __future__ import annotations

import json
import threading
import urllib.request
from typing import Any

from .config import Settings
from .observability import get_logger

_lock = threading.Lock()


def _duration_bucket(duration_ms: float) -> str:
    """Bucket durations so events stay coarse and anonymous."""
    if duration_ms < 50:
        return "<50ms"
    if duration_ms < 250:
        return "50-250ms"
    if duration_ms < 1000:
        return "250ms-1s"
    return ">1s"


def track_tool_usage(
    settings: Settings,
    tool: str,
    *,
    success: bool,
    duration_ms: float,
) -> None:
    """Send one anonymous usage event if analytics are enabled.

    Never raises: analytics failures are logged and ignored.
    """
    if not settings.analytics_enabled:
        return
    fields: dict[str, Any] = {
        "tool": tool,
        "outcome": "success" if success else "error",
        "duration_bucket": _duration_bucket(duration_ms),
        "environment": settings.shlink_env,
    }
    try:
        if settings.analytics_endpoint:
            request = urllib.request.Request(
                settings.analytics_endpoint,
                data=json.dumps(fields).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=2.0) as response:  # noqa: S310
                response.read()
        get_logger(settings.shlink_env).info("analytics.event", **fields)
    except Exception as exc:  # analytics must never break tool execution
        get_logger(settings.shlink_env).warning("analytics.failed", error_type=type(exc).__name__)


def flush() -> None:
    """No-op placeholder for future batching; keeps the call-site API stable."""
    with _lock:
        return None
