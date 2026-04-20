import httpx
from typing import Annotated

from .models import (
    CreateShortUrlRequest,
    ShortUrlResponse,
    ShortUrlDetails,
    ShortUrlListResponse,
    TagListResponse,
)


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

    def _get(self, path: str) -> dict:
        response = self._client.get(f"{self.base_url}/rest/v3{path}")
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, data: dict) -> dict:
        response = self._client.post(f"{self.base_url}/rest/v3{path}", json=data)
        response.raise_for_status()
        return response.json()

    def _delete(self, path: str) -> None:
        response = self._client.delete(f"{self.base_url}/rest/v3{path}")
        response.raise_for_status()

    def create_short_url(self, request: CreateShortUrlRequest) -> ShortUrlResponse:
        data = {"longUrl": request.long_url}
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
        return ShortUrlListResponse(
            data=[
                ShortUrlResponse(
                    short_url=u["shortUrl"],
                    short_code=u["shortCode"],
                    long_url=u["longUrl"],
                    date_created=u["dateCreated"],
                    tags=u.get("tags", []),
                    visits_count=u.get("visitsCount", 0),
                )
                for u in result.get("data", [])
            ],
            pagination=result.get("pagination", {}),
        )

    def get_short_url(self, short_code: str) -> ShortUrlDetails:
        result = self._get(f"/short-urls/{short_code}")
        return ShortUrlDetails(
            short_url=result["shortUrl"],
            short_code=result["shortCode"],
            long_url=result["longUrl"],
            date_created=result["dateCreated"],
            tags=result.get("tags", []),
            visits_count=result.get("visitsCount", 0),
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
    import os

    base_url = os.environ.get("SHLINK_BASE_URL")
    api_key = os.environ.get("SHLINK_API_KEY")

    if not base_url or not api_key:
        raise ValueError("SHLINK_BASE_URL and SHLINK_API_KEY must be set")

    return ShlinkClient(base_url, api_key)
