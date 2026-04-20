from unittest.mock import Mock, patch

import pytest

from mcp_shlink.client import ShlinkClient
from mcp_shlink.models import CreateShortUrlRequest


@pytest.fixture
def mock_client():
    client = ShlinkClient("https://example.com", "test-api-key")
    return client


class TestShlinkClient:
    def test_create_short_url(self, mock_client):
        with patch.object(mock_client._client, "post") as mock_post:
            mock_post.return_value = Mock(
                json=lambda: {
                    "shortUrl": "https://example.com/s/abc123",
                    "shortCode": "abc123",
                    "longUrl": "https://example.com/very/long/url",
                    "dateCreated": "2024-01-15T10:30:00+00:00",
                    "tags": ["test"],
                    "visitsCount": 0,
                }
            )

            request = CreateShortUrlRequest(long_url="https://example.com/very/long/url")
            result = mock_client.create_short_url(request)

            assert result.short_code == "abc123"
            assert result.long_url == "https://example.com/very/long/url"
            mock_post.assert_called_once()

    def test_list_short_urls(self, mock_client):
        with patch.object(mock_client._client, "get") as mock_get:
            mock_get.return_value = Mock(
                json=lambda: {
                    "shortUrls": {
                        "data": [
                            {
                                "shortUrl": "https://example.com/s/abc123",
                                "shortCode": "abc123",
                                "longUrl": "https://example.com/very/long/url",
                                "dateCreated": "2024-01-15T10:30:00+00:00",
                                "tags": [],
                                "visitsSummary": {"total": 5},
                            }
                        ],
                        "pagination": {"currentPage": 1, "pageCount": 1},
                    }
                }
            )

            result = mock_client.list_short_urls()

            assert len(result.data) == 1
            assert result.data[0].short_code == "abc123"
            assert result.data[0].visits_count == 5
            mock_get.assert_called_once()

    def test_get_short_url(self, mock_client):
        with patch.object(mock_client._client, "get") as mock_get:
            mock_get.return_value = Mock(
                json=lambda: {
                    "shortUrl": "https://example.com/s/abc123",
                    "shortCode": "abc123",
                    "longUrl": "https://example.com/very/long/url",
                    "dateCreated": "2024-01-15T10:30:00+00:00",
                    "tags": ["test"],
                    "visitsCount": 10,
                    "meta": {"validUntil": "2025-12-31T23:59:59+00:00"},
                }
            )

            result = mock_client.get_short_url("abc123")

            assert result.short_code == "abc123"
            assert result.meta is not None
            mock_get.assert_called_once()

    def test_delete_short_url(self, mock_client):
        with patch.object(mock_client._client, "delete") as mock_delete:
            mock_delete.return_value = Mock(raise_for_status=lambda: None)

            mock_client.delete_short_url("abc123")

            mock_delete.assert_called_once()

    def test_list_tags(self, mock_client):
        with patch.object(mock_client._client, "get") as mock_get:
            mock_get.return_value = Mock(
                json=lambda: {
                    "data": [
                        {"tag": "test", "shortUrlsCount": 5},
                        {"tag": "prod", "shortUrlsCount": 3},
                    ]
                }
            )

            result = mock_client.list_tags()

            assert len(result.data) == 2
            assert result.data[0].tag == "test"
            mock_get.assert_called_once()
