from mcp.server.fastmcp import FastMCP

from .client import get_client
from .models import (
    CreateShortUrlRequest,
    ShortUrlDetails,
    ShortUrlListResponse,
    ShortUrlResponse,
    TagListResponse,
)

mcp = FastMCP("Shlink")


@mcp.tool()
def create_short_url(
    long_url: str,
    tags: list[str] | None = None,
    custom_slug: str | None = None,
    valid_until: str | None = None,
    max_visits: int | None = None,
) -> ShortUrlResponse:
    """Create a new shortened URL in Shlink."""
    client = get_client()
    try:
        request = CreateShortUrlRequest(
            long_url=long_url,
            tags=tags,
            custom_slug=custom_slug,
            valid_until=valid_until,
            max_visits=max_visits,
        )
        return client.create_short_url(request)
    finally:
        client.close()


@mcp.tool()
def list_short_urls() -> ShortUrlListResponse:
    """List all shortened URLs in Shlink."""
    client = get_client()
    try:
        return client.list_short_urls()
    finally:
        client.close()


@mcp.tool()
def get_short_url(short_code: str) -> ShortUrlDetails:
    """Get details of a shortened URL by its short code."""
    client = get_client()
    try:
        return client.get_short_url(short_code)
    finally:
        client.close()


@mcp.tool()
def delete_short_url(short_code: str) -> str:
    """Delete a shortened URL by its short code."""
    client = get_client()
    try:
        client.delete_short_url(short_code)
        return f"Short URL with code '{short_code}' has been deleted."
    finally:
        client.close()


@mcp.tool()
def list_tags() -> TagListResponse:
    """List all tags in Shlink."""
    client = get_client()
    try:
        return client.list_tags()
    finally:
        client.close()
