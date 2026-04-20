import pytest
from unittest.mock import patch

from mcp_shlink.tools import create_short_url, list_short_urls, delete_short_url


class TestMcpTools:
    @patch("mcp_shlink.tools.get_client")
    def test_create_short_url_tool(self, mock_get_client):
        mock_client = mock_get_client.return_value
        mock_client.create_short_url.return_value.short_code = "abc123"
        mock_client.create_short_url.return_value.long_url = "https://example.com"
        mock_client.create_short_url.return_value.short_url = "https://shlink.io/s/abc123"
        mock_client.create_short_url.return_value.date_created = "2024-01-15T10:30:00+00:00"
        mock_client.create_short_url.return_value.tags = []
        mock_client.create_short_url.return_value.visits_count = 0

        result = create_short_url("https://example.com")

        assert result.short_code == "abc123"
        mock_client.create_short_url.assert_called_once()
        mock_client.close.assert_called_once()

    @patch("mcp_shlink.tools.get_client")
    def test_list_short_urls_tool(self, mock_get_client):
        mock_client = mock_get_client.return_value
        mock_client.list_short_urls.return_value.data = []

        result = list_short_urls()

        assert result.data == []
        mock_client.close.assert_called_once()

    @patch("mcp_shlink.tools.get_client")
    def test_delete_short_url_tool(self, mock_get_client):
        mock_client = mock_get_client.return_value

        result = delete_short_url("abc123")

        assert "deleted" in result.lower()
        mock_client.delete_short_url.assert_called_once_with("abc123")
        mock_client.close.assert_called_once()
