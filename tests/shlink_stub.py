"""Wiremock-style stub responses for the Shlink REST v3 API.

The integration tests import :data:`SHLINK_RESPONSES` instead of hand-writing
HTTP fixtures, so request/response shapes live in one place next to the stub
server that serves them.
"""

from __future__ import annotations

from typing import Any

SHLINK_RESPONSES: dict[str, Any] = {
    "create_short_url": {
        "shortUrl": "http://localhost:8765/abc123",
        "shortCode": "abc123",
        "longUrl": "https://example.com/very/long/url",
        "dateCreated": "2024-01-15T10:30:00+00:00",
        "tags": ["test"],
        "visitsCount": 0,
    },
    "list_short_urls": {
        "shortUrls": {
            "data": [
                {
                    "shortUrl": "http://localhost:8765/abc123",
                    "shortCode": "abc123",
                    "longUrl": "https://example.com/very/long/url",
                    "dateCreated": "2024-01-15T10:30:00+00:00",
                    "tags": ["test"],
                    "visitsSummary": {"total": 5},
                }
            ],
            "pagination": {"currentPage": 1, "pageCount": 1, "totalItems": 1},
        }
    },
    "get_short_url": {
        "shortUrl": "http://localhost:8765/abc123",
        "shortCode": "abc123",
        "longUrl": "https://example.com/very/long/url",
        "dateCreated": "2024-01-15T10:30:00+00:00",
        "tags": ["test"],
        "visitsCount": 10,
        "visitsSummary": {"total": 10},
        "meta": {"validUntil": "2025-12-31T23:59:59+00:00"},
    },
    "list_tags": {
        "data": [
            {"tag": "test", "shortUrlsCount": 5},
            {"tag": "prod", "shortUrlsCount": 3},
        ]
    },
    "delete_short_url": None,
}
