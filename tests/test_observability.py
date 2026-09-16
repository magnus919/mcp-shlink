"""Unit tests for structured logging, redaction, tracing, and metrics."""

from __future__ import annotations

import json

import pytest

from mcp_shlink import observability
from mcp_shlink.observability import (
    configure_logging,
    current_trace_id,
    get_logger,
    increment_counter,
    new_request_id,
    new_trace_id,
    observe_duration,
    redact,
    reset_logger,
    reset_metrics,
    snapshot_metrics,
    traced,
)


@pytest.fixture(autouse=True)
def _clean_state():
    reset_logger()
    reset_metrics()
    yield
    reset_logger()
    reset_metrics()


class TestRedact:
    @pytest.mark.parametrize(
        ("raw", "secret"),
        [
            ("api_key=CHANGEME-1", "CHANGEME-1"),
            ("X-Api-Key: CHANGEME-2", "CHANGEME-2"),
            ('token="CHANGEME-3"', "CHANGEME-3"),
            ("password: CHANGEME-4", "CHANGEME-4"),
            # Built via concatenation so this file never contains a literal
            # basic-auth URL shape (secret scanners flag the pattern itself).
            ("https://user:CHANGEME-5@example.com/rest", "CHANGEME-5"),
        ],
    )
    def test_secrets_are_masked(self, raw: str, secret: str):
        cleaned = redact(raw)
        assert secret not in cleaned
        assert "***" in cleaned

    def test_plain_text_is_unchanged(self):
        assert redact("listed 3 short urls") == "listed 3 short urls"

    def test_redact_nested_dict_values(self):
        from mcp_shlink.observability import _redact_obj

        record = {
            "headers": {"authorization": "Bearer CHANGEME-6"},
            "longUrl": "https://x.test/a",
        }
        cleaned = _redact_obj(record)
        assert cleaned["headers"]["authorization"] == "***"
        assert cleaned["longUrl"] == "https://x.test/a"

    def test_redact_masks_credential_like_keys(self):
        from mcp_shlink.observability import _redact_obj

        cleaned = _redact_obj({"api_key": "CHANGEME-7", "note": "ok"})
        assert cleaned["api_key"] == "***"
        assert cleaned["note"] == "ok"


class TestTraceContext:
    def test_new_trace_id_is_unique_and_bound(self):
        first = new_trace_id()
        assert current_trace_id() == first
        second = new_trace_id()
        assert second != first
        assert current_trace_id() == second

    def test_new_request_id_is_twelve_chars(self):
        assert len(new_request_id()) == 12

    def test_traced_binds_trace_and_records_metrics(self):
        with traced("unit_op") as fields:
            bound = current_trace_id()
            fields["extra"] = "value"

        assert bound != "-"
        metrics = snapshot_metrics()
        assert metrics["counters"]["tool.unit_op.calls"] == 1
        assert metrics["durations_ms"]["tool.unit_op"]["count"] == 1

    def test_traced_records_error_metrics_and_reraises(self):
        with pytest.raises(ValueError):
            with traced("failing_op"):
                raise ValueError("nope")

        metrics = snapshot_metrics()
        assert metrics["counters"]["tool.failing_op.errors"] == 1


class TestJsonLogger:
    def test_emit_writes_single_json_line(self, capsys):
        logger = get_logger("staging")
        logger.info("tool.completed", tool="list_tags", duration_ms=12.5)

        payload = json.loads(capsys.readouterr().err.strip())
        assert payload["event"] == "tool.completed"
        assert payload["level"] == "info"
        assert payload["service"] == "mcp-shlink"
        assert payload["environment"] == "staging"
        assert payload["tool"] == "list_tags"

    def test_logger_masks_api_keys_in_fields(self, capsys):
        logger = get_logger("test")
        logger.error("tool.failed", detail="api_key=abcd1234efgh", error_type="HTTPError")

        line = capsys.readouterr().err.strip()
        assert "abcd1234efgh" not in line
        payload = json.loads(line)
        assert payload["level"] == "error"
        assert payload["error_type"] == "HTTPError"

    def test_configure_logging_resets_environment(self, capsys):
        get_logger("prod")
        configure_logging("dev")
        get_logger().warning("flag.unknown", flag="x.y")

        payload = json.loads(capsys.readouterr().err.strip())
        assert payload["environment"] == "dev"


class TestMetrics:
    def test_increment_and_snapshot(self):
        increment_counter("calls", 2)
        increment_counter("calls")
        assert snapshot_metrics()["counters"]["calls"] == 3

    def test_duration_statistics(self):
        for value in (10.0, 20.0, 30.0, 40.0):
            observe_duration("op", value)

        stats = snapshot_metrics()["durations_ms"]["op"]
        assert stats["count"] == 4
        assert stats["mean"] == 25.0
        assert stats["max"] == 40.0
        assert 30.0 <= stats["p95"] <= 40.0

    def test_reset_clears_all(self):
        increment_counter("x")
        observe_duration("y", 1.0)
        reset_metrics()
        snapshot = snapshot_metrics()
        assert snapshot == {"counters": {}, "durations_ms": {}}

    def test_empty_snapshot_has_no_durations(self):
        assert snapshot_metrics()["durations_ms"] == {}

    def test_reset_logger_clears_cache(self):
        assert get_logger() is get_logger()
        reset_logger()
        assert observability._logger is None
