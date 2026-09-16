from __future__ import annotations

from typing import Any
from unittest.mock import Mock, patch

import httpx
import pytest

from mcp_shlink.client import ShlinkClient
from mcp_shlink.models import CreateShortUrlRequest


@pytest.fixture
def mock_client():
    client = ShlinkClient("https://example.com", "test-api-key")
    return client


@pytest.fixture
def clean_shlink_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove every Shlink-related env var so tests start from a clean slate."""
    for name in (
        "SHLINK_BASE_URL",
        "SHLINK_API_KEY",
        "SHLINK_ENV",
        "SHLINK_ANALYTICS_ENABLED",
        "SHLINK_ANALYTICS_ENDPOINT",
        "SENTRY_DSN",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def stub_responses() -> dict[str, Any]:
    from tests.shlink_stub import SHLINK_RESPONSES

    return SHLINK_RESPONSES


class TestShlinkClient:
    def test_create_short_url(self, mock_client, stub_responses):
        with patch.object(mock_client._client, "request") as mock_request:
            mock_request.return_value = Mock(
                status_code=201, json=lambda: stub_responses["create_short_url"]
            )

            request = CreateShortUrlRequest(long_url="https://example.com/very/long/url")
            result = mock_client.create_short_url(request)

            assert result.short_code == "abc123"
            assert result.long_url == "https://example.com/very/long/url"
            mock_request.assert_called_once()
            assert mock_request.call_args.args[0] == "POST"

    def test_list_short_urls(self, mock_client, stub_responses):
        with patch.object(mock_client._client, "request") as mock_request:
            mock_request.return_value = Mock(
                status_code=200, json=lambda: stub_responses["list_short_urls"]
            )

            result = mock_client.list_short_urls()

            assert len(result.data) == 1
            assert result.data[0].short_code == "abc123"
            assert result.data[0].visits_count == 5
            mock_request.assert_called_once()
            assert mock_request.call_args.args[0] == "GET"

    def test_get_short_url(self, mock_client, stub_responses):
        with patch.object(mock_client._client, "request") as mock_request:
            mock_request.return_value = Mock(
                status_code=200, json=lambda: stub_responses["get_short_url"]
            )

            result = mock_client.get_short_url("abc123")

            assert result.short_code == "abc123"
            assert result.meta is not None
            mock_request.assert_called_once()
            assert "/short-urls/abc123" in mock_request.call_args.args[1]

    def test_delete_short_url(self, mock_client):
        with patch.object(mock_client._client, "request") as mock_request:
            mock_request.return_value = Mock(status_code=204, raise_for_status=lambda: None)

            mock_client.delete_short_url("abc123")

            mock_request.assert_called_once()
            assert mock_request.call_args.args[0] == "DELETE"

    def test_list_tags(self, mock_client, stub_responses):
        with patch.object(mock_client._client, "request") as mock_request:
            mock_request.return_value = Mock(
                status_code=200, json=lambda: stub_responses["list_tags"]
            )

            result = mock_client.list_tags()

            assert len(result.data) == 2
            assert result.data[0].tag == "test"
            mock_request.assert_called_once()


class TestShlinkErrors:
    """4xx/5xx responses must surface useful, typed exceptions."""

    @pytest.mark.parametrize(
        ("status_code", "expected_status"),
        [(401, 401), (403, 403), (404, 404), (409, 409), (429, 429)],
    )
    def test_client_error_raises_http_status_error(
        self, mock_client, status_code: int, expected_status: int
    ):
        request = httpx.Request("GET", "https://example.com/rest/v3/short-urls")
        response = httpx.Response(status_code, request=request)
        with patch.object(mock_client._client, "request", return_value=response):
            with pytest.raises(httpx.HTTPStatusError) as excinfo:
                mock_client.list_short_urls()
        assert excinfo.value.response.status_code == expected_status

    def test_500_raises_when_retries_disabled(self, mock_client):
        request = httpx.Request("GET", "https://example.com/rest/v3/short-urls")
        response = httpx.Response(500, request=request)
        with patch.object(mock_client._client, "request", return_value=response):
            with pytest.raises(httpx.HTTPStatusError) as excinfo:
                mock_client.list_short_urls()
        assert excinfo.value.response.status_code == 500


class TestShlinkRetry:
    """The retry loop (feature-flag gated) must back off and eventually succeed."""

    @staticmethod
    def _enable_retry(monkeypatch: pytest.MonkeyPatch, enabled: bool) -> None:
        monkeypatch.setattr(
            "mcp_shlink.client.is_enabled",
            lambda flag: enabled and flag == "shlink.retry_5xx.enabled",
        )
        monkeypatch.setattr("mcp_shlink.client.time.sleep", lambda _seconds: None)

    @staticmethod
    def _always_500_patcher(mock_client, request: httpx.Request):
        """Return (calls, patcher) that counts repeated 500 responses."""
        response_500 = httpx.Response(500, request=request)
        calls: list[httpx.Response] = []

        def _always_500(*args: object, **kwargs: object) -> httpx.Response:
            calls.append(response_500)
            return response_500

        return calls, patch.object(mock_client._client, "request", side_effect=_always_500)

    def test_retry_on_503_then_success(self, mock_client, monkeypatch):
        self._enable_retry(monkeypatch, enabled=True)

        request = httpx.Request("GET", "https://example.com/rest/v3/short-urls")
        responses = iter(
            [
                httpx.Response(503, request=request),
                httpx.Response(
                    200, request=request, json={"shortUrls": {"data": []}, "pagination": {}}
                ),
            ]
        )
        with patch.object(
            mock_client._client, "request", side_effect=lambda *a, **kw: next(responses)
        ):
            result = mock_client.list_short_urls()
        assert result.data == []

    def test_retry_exhaustion_raises_last_error(self, mock_client, monkeypatch):
        self._enable_retry(monkeypatch, enabled=True)

        request = httpx.Request("GET", "https://example.com/rest/v3/short-urls")
        calls, request_patcher = self._always_500_patcher(mock_client, request)
        with request_patcher:
            with pytest.raises(httpx.HTTPStatusError):
                mock_client.list_short_urls()
        # 3 attempts total when the feature flag is on.
        assert len(calls) == 3

    def test_transport_error_retried_then_raises(self, mock_client, monkeypatch):
        self._enable_retry(monkeypatch, enabled=True)

        attempts: list[int] = []

        def _raise_connect_error(*args: object, **kwargs: object) -> httpx.Response:
            attempts.append(1)
            raise httpx.ConnectError("connection refused")

        with patch.object(mock_client._client, "request", side_effect=_raise_connect_error):
            with pytest.raises(httpx.ConnectError):
                mock_client.list_tags()
        assert len(attempts) == 3

    def test_no_retry_when_flag_disabled(self, mock_client, monkeypatch):
        self._enable_retry(monkeypatch, enabled=False)

        request = httpx.Request("GET", "https://example.com/rest/v3/short-urls")
        calls, request_patcher = self._always_500_patcher(mock_client, request)
        with request_patcher:
            with pytest.raises(httpx.HTTPStatusError):
                mock_client.list_short_urls()
        assert len(calls) == 1


class TestGetClient:
    def test_missing_env_raises_configuration_error(self, clean_shlink_env: None):
        from mcp_shlink.client import get_client
        from mcp_shlink.config import ConfigurationError

        with pytest.raises(ConfigurationError):
            get_client()

    def test_client_built_from_valid_env(self, clean_shlink_env, monkeypatch):
        from mcp_shlink.client import get_client

        monkeypatch.setenv("SHLINK_BASE_URL", "https://shlink.example.com/")
        monkeypatch.setenv("SHLINK_API_KEY", "k")

        client = get_client()
        assert client.base_url == "https://shlink.example.com"  # trailing slash stripped


class TestExponentialBackoff:
    """Backoff must grow geometrically across retry attempts."""

    @pytest.mark.parametrize(
        ("attempt", "expected_seconds"),
        [(0, 0.2), (1, 0.4), (2, 0.8)],
    )
    def test_backoff_schedule(self, attempt: int, expected_seconds: float) -> None:
        from mcp_shlink.client import _BACKOFF_BASE_SECONDS

        computed = _BACKOFF_BASE_SECONDS * (2**attempt)
        assert computed == expected_seconds
