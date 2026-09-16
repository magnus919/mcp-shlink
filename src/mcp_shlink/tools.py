"""MCP tool definitions for the Shlink server.

Every tool runs inside :func:`mcp_shlink.observability.traced`, which binds a
trace id, records duration/error metrics, and emits one structured log event.
Tool usage analytics are opt-in (see :mod:`mcp_shlink.analytics`).
"""

from __future__ import annotations

import time
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from .analytics import track_tool_usage
from .client import get_client
from .config import load_settings
from .features import is_enabled
from .models import (
    CreateShortUrlRequest,
    ShortUrlDetails,
    ShortUrlListResponse,
    ShortUrlResponse,
    TagListResponse,
)
from .observability import configure_logging, get_logger, snapshot_metrics, traced

mcp = FastMCP("Shlink")

_SOFT_DELETE_GRACE_DAYS = 7


@mcp.tool()
def create_short_url(
    long_url: str,
    tags: list[str] | None = None,
    custom_slug: str | None = None,
    valid_until: str | None = None,
    max_visits: int | None = None,
) -> ShortUrlResponse:
    """Create a new shortened URL in Shlink."""
    settings = load_settings()
    logger = configure_logging(settings.shlink_env)
    start = time.perf_counter()
    with traced("create_short_url", logger) as fields:
        client = get_client()
        try:
            request = CreateShortUrlRequest(
                long_url=long_url,
                tags=tags,
                custom_slug=custom_slug,
                valid_until=valid_until,
                max_visits=max_visits,
            )
            result = client.create_short_url(request)
            fields["outcome"] = "created"
            return result
        finally:
            client.close()
            track_tool_usage(
                settings,
                "create_short_url",
                success=True,
                duration_ms=(time.perf_counter() - start) * 1000,
            )


@mcp.tool()
def list_short_urls() -> ShortUrlListResponse:
    """List all shortened URLs in Shlink."""
    settings = load_settings()
    logger = get_logger(settings.shlink_env)
    start = time.perf_counter()
    with traced("list_short_urls", logger):
        client = get_client()
        try:
            return client.list_short_urls()
        finally:
            client.close()
            track_tool_usage(
                settings,
                "list_short_urls",
                success=True,
                duration_ms=(time.perf_counter() - start) * 1000,
            )


@mcp.tool()
def get_short_url(short_code: str) -> ShortUrlDetails:
    """Get details of a shortened URL by its short code."""
    settings = load_settings()
    logger = get_logger(settings.shlink_env)
    start = time.perf_counter()
    with traced("get_short_url", logger) as fields:
        client = get_client()
        try:
            result = client.get_short_url(short_code)
            fields["short_code"] = short_code
            return result
        finally:
            client.close()
            track_tool_usage(
                settings,
                "get_short_url",
                success=True,
                duration_ms=(time.perf_counter() - start) * 1000,
            )


@mcp.tool()
def delete_short_url(short_code: str, ctx: Context | None = None) -> str:  # type: ignore[type-arg]
    """Delete a shortened URL by its short code.

    When the ``shlink.soft_delete.enabled`` feature flag is on, deletion is
    staged: the tool reports a grace period and the caller must confirm before
    the URL is actually removed.
    """
    settings = load_settings()
    logger = get_logger(settings.shlink_env)
    start = time.perf_counter()
    with traced("delete_short_url", logger) as fields:
        client = get_client()
        try:
            if is_enabled("shlink.soft_delete.enabled"):
                confirm = ctx and getattr(ctx, "request_context", None) is not None
                fields["mode"] = "soft_delete"
                if not confirm:
                    return (
                        f"Soft delete enabled: short URL '{short_code}' is staged for deletion"
                        f" with a {_SOFT_DELETE_GRACE_DAYS}-day grace period."
                        " Call again with confirmation to remove it permanently."
                    )
            result_message = f"Short URL with code '{short_code}' has been deleted."
            client.delete_short_url(short_code)
            fields["short_code"] = short_code
            return result_message
        finally:
            client.close()
            track_tool_usage(
                settings,
                "delete_short_url",
                success=True,
                duration_ms=(time.perf_counter() - start) * 1000,
            )


@mcp.tool()
def list_tags() -> TagListResponse:
    """List all tags in Shlink."""
    settings = load_settings()
    logger = get_logger(settings.shlink_env)
    start = time.perf_counter()
    with traced("list_tags", logger):
        client = get_client()
        try:
            return client.list_tags()
        finally:
            client.close()
            track_tool_usage(
                settings,
                "list_tags",
                success=True,
                duration_ms=(time.perf_counter() - start) * 1000,
            )


@mcp.tool()
def get_metrics() -> dict[str, Any]:
    """Return in-process metrics: per-tool call counts, error counts, and latencies.

    Useful for checking server health after a burst of tool calls; counters are
    cumulative for the lifetime of the process.
    """
    settings = load_settings()
    logger = get_logger(settings.shlink_env)
    with traced("get_metrics", logger):
        return snapshot_metrics()
