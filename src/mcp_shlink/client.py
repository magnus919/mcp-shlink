"""HTTP client for the Shlink REST v3 API.

Includes retry with exponential backoff for transient upstream failures
(5xx responses and connection errors), which acts as a lightweight circuit
breaker so a flaky Shlink instance cannot fail every tool call.
"""

from __future__ import annotations

import time
from typing import Annotated, Any

import httpx

from .features import is_enabled
from .models import (
    CreateShortUrlRequest,
    ShortUrlDetails,
    ShortUrlListResponse,
    ShortUrlResponse,
    TagListResponse,
    TagResponse,
)

_MAX_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 0.2


class ShlinkClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(
            headers={"X-Api-Key": api_key},
            timeout=30.0,
        )

    def close(self) -> None:
        self._client.close()

    def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Send a request, retrying 5xx/connection failures with backoff.

        The retry loop is gated behind the ``shlink.retry_5xx.enabled`` feature
        flag so the behavior can be rolled out gradually.
        """
        retries = _MAX_ATTEMPTS if is_enabled("shlink.retry_5xx.enabled") else 1
        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                response = self._client.request(
                    method,
                    f"{self.base_url}/rest/v3{path}",
                    json=json_body,
                )
            except httpx.TransportError as exc:
                last_error = exc
            else:
                if response.status_code < 500:
                    response.raise_for_status()
                    return response
                last_error = httpx.HTTPStatusError(
                    f"upstream returned {response.status_code}",
                    request=response.request,
                    response=response,
                )
            if attempt < retries - 1:
                time.sleep(_BACKOFF_BASE_SECONDS * (2**attempt))
        assert last_error is not None  # retries >= 1 guarantees an error is set
        raise last_error

    def _get(self, path: str) -> dict[str, Any]:
        response = self._request_with_retry("GET", path)
        return response.json()  # type: ignore[no-any-return]

    def _post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        response = self._request_with_retry("POST", path, json_body=data)
        return response.json()  # type: ignore[no-any-return]

    def _delete(self, path: str) -> None:
        self._request_with_retry("DELETE", path)

    def create_short_url(self, request: CreateShortUrlRequest) -> ShortUrlResponse:
        data: dict[str, Any] = {"longUrl": request.long_url}
        if request.tags is not None:
            data["tags"] = request.tags
        if request.custom_slug is not None:
            data["customSlug"] = request.custom_slug
        if request.valid_until is not None:
            data["validUntil"] = request.valid_until
        if request.max_visits is not None:
            data["maxVisits"] = request.max_visits

        result = self._post("/short-urls", data)
        return ShortUrlResponse(
            short_url=result["shortUrl"],
            short_code=result["shortCode"],
            long_url=result["longUrl"],
            date_created=result["dateCreated"],
            tags=result.get("tags", []),
            visits_count=result.get("visitsCount", 0),
        )

    def list_short_urls(self) -> ShortUrlListResponse:
        result = self._get("/short-urls")
        short_urls = result.get("shortUrls", {})
        return ShortUrlListResponse(
            data=[
                ShortUrlResponse(
                    short_url=u["shortUrl"],
                    short_code=u["shortCode"],
                    long_url=u["longUrl"],
                    date_created=u["dateCreated"],
                    tags=u.get("tags", []),
                    visits_count=u.get("visitsSummary", {}).get("total", 0),
                )
                for u in short_urls.get("data", [])
            ],
            pagination=short_urls.get("pagination", {}),
        )

    def get_short_url(self, short_code: str) -> ShortUrlDetails:
        result = self._get(f"/short-urls/{short_code}")
        return ShortUrlDetails(
            short_url=result["shortUrl"],
            short_code=result["shortCode"],
            long_url=result["longUrl"],
            date_created=result["dateCreated"],
            tags=result.get("tags", []),
            visits_count=result.get("visitsSummary", {}).get("total", 0),
            meta=result.get("meta"),
        )

    def delete_short_url(self, short_code: str) -> None:
        self._delete(f"/short-urls/{short_code}")

    def list_tags(self) -> TagListResponse:
        result = self._get("/tags")
        return TagListResponse(
            data=[
                TagResponse(
                    tag=t["tag"],
                    short_urls_count=t["shortUrlsCount"],
                )
                for t in result.get("data", [])
            ]
        )


def get_client() -> Annotated[ShlinkClient, "Requires SHLINK_BASE_URL and SHLINK_API_KEY"]:
    """Build a client from validated settings loaded from the environment."""
    from .config import load_settings

    settings = load_settings()
    return ShlinkClient(settings.base_url, settings.api_key)
