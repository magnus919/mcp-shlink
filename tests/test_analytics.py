"""Unit tests for opt-in analytics instrumentation."""

from __future__ import annotations

import json
import urllib.error
from typing import Any
from unittest.mock import patch

import pytest

from mcp_shlink.analytics import _duration_bucket, track_tool_usage
from mcp_shlink.config import Settings


def _settings(**overrides: Any) -> Settings:
    defaults: dict[str, Any] = {
        "base_url": "https://shlink.example.com",
        "api_key": "k",
        "shlink_env": "test",
        "analytics_enabled": False,
        "analytics_endpoint": None,
    }
    defaults.update(overrides)
    return Settings(**defaults)


class TestDurationBucket:
    @pytest.mark.parametrize(
        ("ms", "expected"),
        [(10, "<50ms"), (60, "50-250ms"), (300, "250ms-1s"), (2000, ">1s")],
    )
    def test_buckets(self, ms: float, expected: str):
        assert _duration_bucket(ms) == expected


class TestTrackToolUsage:
    def test_disabled_by_default_no_output(self, capsys):
        track_tool_usage(_settings(), "list_tags", success=True, duration_ms=12.0)
        assert capsys.readouterr().err == ""

    def test_enabled_without_endpoint_logs_event(self, capsys):
        track_tool_usage(
            _settings(analytics_enabled=True), "list_tags", success=True, duration_ms=80.0
        )
        payload = json.loads(capsys.readouterr().err.strip())
        assert payload["event"] == "analytics.event"
        assert payload["tool"] == "list_tags"
        assert payload["outcome"] == "success"
        assert payload["duration_bucket"] == "50-250ms"
        # No raw URL, slug, or credential may appear in the event payload.
        serialized = json.dumps(payload)
        assert "https://" not in serialized
        assert "api_key" not in serialized

    def test_endpoint_receives_post(self, capsys):
        posted: dict[str, Any] = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args: object):
                return None

            def read(self):
                return b"ok"

        def fake_urlopen(request: Any, timeout: float):
            posted["data"] = request.data
            posted["method"] = request.method
            return FakeResponse()

        with patch("mcp_shlink.analytics.urllib.request.urlopen", side_effect=fake_urlopen):
            track_tool_usage(
                _settings(analytics_enabled=True, analytics_endpoint="http://collector.test/hook"),
                "create_short_url",
                success=True,
                duration_ms=1500.0,
            )

        assert posted["method"] == "POST"
        event = json.loads(posted["data"])
        assert event["tool"] == "create_short_url"
        assert event["duration_bucket"] == ">1s"

    def test_endpoint_failure_swallowed_and_logged(self, capsys):
        def raise_http_error(*args: object, **kwargs: object):
            raise urllib.error.URLError("collector down")

        with patch("mcp_shlink.analytics.urllib.request.urlopen", side_effect=raise_http_error):
            track_tool_usage(
                _settings(analytics_enabled=True, analytics_endpoint="http://collector.test/hook"),
                "get_short_url",
                success=False,
                duration_ms=30.0,
            )

        payload = json.loads(capsys.readouterr().err.strip())
        assert payload["event"] == "analytics.failed"
        assert payload["level"] == "warning"
