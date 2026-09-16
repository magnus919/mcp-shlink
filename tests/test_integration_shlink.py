"""Integration tests: the real httpx client against a local Shlink stub.

These tests start :mod:`tests.shlink_stub_server` on an ephemeral port, point a
real :class:`~mcp_shlink.client.ShlinkClient` at it, and exercise the full HTTP
path (headers, JSON parsing, status handling). No mocked transports and no
network egress.
"""

from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest

from mcp_shlink.client import ShlinkClient
from mcp_shlink.models import CreateShortUrlRequest
from tests.shlink_stub_server import _reset_store, running_stub

STUB_API_KEY = "changeme"


@pytest.fixture
def shlink_base_url() -> Iterator[str]:
    _reset_store()
    with running_stub(api_key=STUB_API_KEY) as (base_url, _server):
        yield base_url
    _reset_store()


@pytest.fixture
def client(shlink_base_url: str) -> Iterator[ShlinkClient]:
    created = ShlinkClient(shlink_base_url, STUB_API_KEY)
    try:
        yield created
    finally:
        created.close()


class TestShortUrlLifecycle:
    """End-to-end CRUD against the stub API."""

    def test_create_then_get_then_delete(self, client: ShlinkClient):
        request = CreateShortUrlRequest(
            long_url="https://example.com/a/very/long/path",
            tags=["integration"],
            custom_slug="itest01",
        )

        created = client.create_short_url(request)
        assert created.short_code == "itest01"
        assert created.long_url == "https://example.com/a/very/long/path"
        assert created.tags == ["integration"]

        fetched = client.get_short_url("itest01")
        assert fetched.short_code == "itest01"
        assert fetched.long_url == created.long_url

        client.delete_short_url("itest01")

        with pytest.raises(httpx.HTTPStatusError) as excinfo:
            client.get_short_url("itest01")
        assert excinfo.value.response.status_code == 404

    def test_list_short_urls_reflects_created_entries(self, client: ShlinkClient):
        assert client.list_short_urls().data == []

        client.create_short_url(CreateShortUrlRequest(long_url="https://a.test/1"))
        client.create_short_url(CreateShortUrlRequest(long_url="https://a.test/2"))

        listing = client.list_short_urls()
        assert len(listing.data) == 2
        assert {item.long_url for item in listing.data} == {"https://a.test/1", "https://a.test/2"}
        assert listing.pagination["totalItems"] == 2

    def test_auto_generated_slug_returned(self, client: ShlinkClient):
        created = client.create_short_url(CreateShortUrlRequest(long_url="https://a.test/x"))
        assert created.short_code
        assert len(created.short_code) == 6


class TestTagsIntegration:
    def test_tags_counts_track_short_urls(self, client: ShlinkClient):
        assert client.list_tags().data == []

        client.create_short_url(
            CreateShortUrlRequest(long_url="https://a.test/1", tags=["docs", "team"])
        )
        client.create_short_url(CreateShortUrlRequest(long_url="https://a.test/2", tags=["docs"]))

        tags = {tag.tag: tag.short_urls_count for tag in client.list_tags().data}
        assert tags == {"docs": 2, "team": 1}

    def test_tag_count_decrements_after_delete(self, client: ShlinkClient):
        client.create_short_url(
            CreateShortUrlRequest(long_url="https://a.test/1", tags=["temp"], custom_slug="tagdel")
        )
        assert client.list_tags().data[0].short_urls_count == 1

        client.delete_short_url("tagdel")

        assert client.list_tags().data == []


class TestAuthenticationAndErrors:
    def test_wrong_api_key_is_rejected(self, shlink_base_url: str):
        bad_client = ShlinkClient(shlink_base_url, "wrong-key")
        try:
            with pytest.raises(httpx.HTTPStatusError) as excinfo:
                bad_client.list_tags()
            assert excinfo.value.response.status_code == 401
        finally:
            bad_client.close()

    def test_unknown_short_code_returns_404(self, client: ShlinkClient):
        with pytest.raises(httpx.HTTPStatusError) as excinfo:
            client.get_short_url("does-not-exist")
        assert excinfo.value.response.status_code == 404

    def test_delete_unknown_short_code_returns_404(self, client: ShlinkClient):
        with pytest.raises(httpx.HTTPStatusError) as excinfo:
            client.delete_short_url("never-existed")
        assert excinfo.value.response.status_code == 404


class TestRealToolsAgainstStub:
    """Drive the MCP tool layer against the live stub (no client mocking)."""

    def test_list_tags_tool_with_real_client(
        self, shlink_base_url: str, monkeypatch: pytest.MonkeyPatch
    ):
        from mcp_shlink import tools
        from mcp_shlink.observability import snapshot_metrics

        monkeypatch.setenv("SHLINK_BASE_URL", shlink_base_url)
        monkeypatch.setenv("SHLINK_API_KEY", STUB_API_KEY)
        monkeypatch.setenv("SHLINK_ENV", "integration")

        result = tools.list_tags()

        assert result.data == []
        assert snapshot_metrics()["counters"]["tool.list_tags.calls"] == 1

    def test_create_short_url_tool_with_real_client(
        self, shlink_base_url: str, monkeypatch: pytest.MonkeyPatch
    ):
        from mcp_shlink import tools

        monkeypatch.setenv("SHLINK_BASE_URL", shlink_base_url)
        monkeypatch.setenv("SHLINK_API_KEY", STUB_API_KEY)
        monkeypatch.setenv("SHLINK_ENV", "integration")

        created = tools.create_short_url("https://example.com/from-tool", custom_slug="tool01")

        assert created.short_code == "tool01"
        assert client_round_trip(shlink_base_url, "tool01") is True


def client_round_trip(base_url: str, short_code: str) -> bool:
    """Verify a short URL created through the tool layer is fetchable via REST."""
    probe = ShlinkClient(base_url, STUB_API_KEY)
    try:
        return probe.get_short_url(short_code).short_code == short_code
    finally:
        probe.close()
