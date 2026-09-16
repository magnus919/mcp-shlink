from __future__ import annotations

import json
import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from mcp_shlink import tools
from mcp_shlink.config import Settings
from mcp_shlink.observability import (
    current_trace_id,
    reset_logger,
    reset_metrics,
    snapshot_metrics,
)


@pytest.fixture(autouse=True)
def _isolate_observability(monkeypatch: pytest.MonkeyPatch):
    """Reset metrics/logger state and point env at a dummy instance per test."""
    reset_metrics()
    reset_logger()
    monkeypatch.setenv("SHLINK_BASE_URL", "https://shlink.example.com")
    monkeypatch.setenv("SHLINK_API_KEY", "test-key")
    monkeypatch.setenv("SHLINK_ENV", "test")
    yield
    reset_metrics()
    reset_logger()


def _mock_client_factory(**overrides: Any) -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.short_code = "abc123"
    response.long_url = "https://example.com"
    response.short_url = "https://shlink.io/s/abc123"
    response.date_created = "2024-01-15T10:30:00+00:00"
    response.tags = []
    response.visits_count = 0
    client.create_short_url.return_value = response
    listing = MagicMock()
    listing.data = []
    client.list_short_urls.return_value = listing
    for key, value in overrides.items():
        setattr(client, key, value)
    factory = MagicMock(return_value=client)
    return factory


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

        result = tools.create_short_url("https://example.com")

        assert result.short_code == "abc123"
        mock_client.create_short_url.assert_called_once()
        mock_client.close.assert_called_once()

    @patch("mcp_shlink.tools.get_client")
    def test_list_short_urls_tool(self, mock_get_client):
        mock_client = mock_get_client.return_value
        mock_client.list_short_urls.return_value.data = []

        result = tools.list_short_urls()

        assert result.data == []
        mock_client.close.assert_called_once()

    @patch("mcp_shlink.tools.get_client")
    def test_delete_short_url_tool(self, mock_get_client):
        mock_client = mock_get_client.return_value

        result = tools.delete_short_url("abc123")

        assert "deleted" in result.lower()
        mock_client.delete_short_url.assert_called_once_with("abc123")
        mock_client.close.assert_called_once()


class TestTracingAndMetrics:
    """Every tool must bind a trace id and record call metrics."""

    @patch("mcp_shlink.tools.get_client")
    def test_trace_id_bound_during_tool(self, mock_get_client):
        seen_trace: dict[str, str] = {}

        client = MagicMock()
        client.list_short_urls.side_effect = lambda: (
            seen_trace.update(trace=current_trace_id()) or MagicMock(data=[])
        )
        mock_get_client.side_effect = _mock_client_factory(list_short_urls=client.list_short_urls)

        tools.list_short_urls()

        assert seen_trace["trace"] == current_trace_id()
        assert seen_trace["trace"] != "-"

    @patch("mcp_shlink.tools.get_client")
    def test_metrics_recorded_after_calls(self, mock_get_client):
        mock_get_client.side_effect = _mock_client_factory()

        tools.list_short_urls()
        tools.list_tags()

        metrics = snapshot_metrics()
        assert metrics["counters"]["tool.list_short_urls.calls"] == 1
        assert metrics["counters"]["tool.list_tags.calls"] == 1
        assert "tool.list_short_urls" in metrics["durations_ms"]

    @patch("mcp_shlink.tools.get_client")
    def test_error_metrics_recorded_on_failure(self, mock_get_client):
        factory = _mock_client_factory()
        factory.return_value.list_tags.side_effect = RuntimeError("boom")
        mock_get_client.side_effect = factory

        with pytest.raises(RuntimeError, match="boom"):
            tools.list_tags()

        metrics = snapshot_metrics()
        assert metrics["counters"]["tool.list_tags.errors"] == 1
        assert "tool.list_tags" in metrics["durations_ms"]


class TestStructuredToolLogs:
    """Tool completions must emit one JSON log line with trace and duration."""

    @patch("mcp_shlink.tools.get_client")
    def test_tool_completion_log_line(self, mock_get_client, capsys):
        mock_get_client.side_effect = _mock_client_factory()

        tools.list_short_urls()

        captured = capsys.readouterr()
        lines = [line for line in captured.err.splitlines() if line.strip()]
        assert lines, "expected at least one JSON log line on stderr"
        events = [json.loads(line) for line in lines]
        completed = [e for e in events if e.get("event") == "tool.completed"]
        assert completed, f"no tool.completed event in {events}"
        event = completed[-1]
        assert event["tool"] == "list_short_urls"
        assert event["level"] == "info"
        assert event["service"] == "mcp-shlink"
        assert isinstance(event["duration_ms"], float)


class TestSoftDeleteFeatureFlag:
    """delete_short_url honours the shlink.soft_delete.enabled flag."""

    @patch("mcp_shlink.tools.get_client")
    def test_soft_delete_staged_when_flag_on(self, mock_get_client, monkeypatch):
        monkeypatch.setattr(
            "mcp_shlink.tools.is_enabled", lambda flag: flag == "shlink.soft_delete.enabled"
        )
        factory = _mock_client_factory()
        mock_get_client.side_effect = factory

        result = tools.delete_short_url("abc123")

        assert "staged for deletion" in result
        factory.return_value.delete_short_url.assert_not_called()

    @patch("mcp_shlink.tools.get_client")
    def test_hard_delete_when_flag_off(self, mock_get_client):
        factory = _mock_client_factory()
        mock_get_client.side_effect = factory

        result = tools.delete_short_url("abc123")

        assert "has been deleted" in result
        factory.return_value.delete_short_url.assert_called_once_with("abc123")


class TestGetMetricsTool:
    @patch("mcp_shlink.tools.get_client")
    def test_get_metrics_tool(self, mock_get_client):
        mock_get_client.side_effect = _mock_client_factory()

        tools.list_short_urls()
        report = tools.get_metrics()

        assert report["counters"]["tool.list_short_urls.calls"] == 1


class TestToolUsageAnalytics:
    """Opt-in analytics event per successful tool call."""

    @patch("mcp_shlink.tools.get_client")
    def test_analytics_event_emitted_when_enabled(self, mock_get_client, monkeypatch):
        monkeypatch.setenv("SHLINK_ANALYTICS_ENABLED", "true")
        events: list[dict] = []

        def fake_track(settings: Settings, tool: str, *, success: bool, duration_ms: float) -> None:
            events.append({"tool": tool, "success": success, "duration_ms": duration_ms})

        monkeypatch.setattr(tools, "track_tool_usage", fake_track)
        mock_get_client.side_effect = _mock_client_factory()

        tools.list_short_urls()

        assert events and events[0]["tool"] == "list_short_urls" and events[0]["success"] is True

    @patch("mcp_shlink.tools.get_client")
    def test_analytics_disabled_by_default(self, mock_get_client, monkeypatch):
        monkeypatch.delenv("SHLINK_ANALYTICS_ENABLED", raising=False)
        called: list[str] = []
        monkeypatch.setattr(
            tools,
            "track_tool_usage",
            lambda *args, **kwargs: called.append("called"),
        )
        mock_get_client.side_effect = _mock_client_factory()

        settings = tools.load_settings()
        assert settings.analytics_enabled is False
        tools.list_short_urls()
        # track_tool_usage is still invoked but returns early when disabled.
        assert called == ["called"]


class TestEnvSanity:
    def test_no_real_credentials_in_test_env(self) -> None:
        # The suite must never depend on (or leak) real Shlink credentials.
        assert os.environ.get("SHLINK_BASE_URL", "unset") in {"https://shlink.example.com", "unset"}
