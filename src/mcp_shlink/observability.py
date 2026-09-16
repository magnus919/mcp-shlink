"""Structured logging, secret redaction, trace IDs, and metrics.

Everything is stdlib-only so the server stays dependency-light:

- JSON logs go to stderr (stdio transport owns stdout).
- One bound context includes ``trace_id``, ``request_id``, and ``environment``.
- Credentials, tokens, and URLs are redacted before a record is written.
- ``tools/list`` responses never reach the log (they can embed user URLs).
- Counters and durations are kept in-process and dumped at shutdown.
"""

from __future__ import annotations

import json
import re
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

# Matches values of keys that look secret-bearing, plus URLs that can embed keys.
_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"(?i)((?:api[_-]?key|token|secret|password|authorization)\s*[\"']?\s*[:=]\s*[\"']?)([^\"'\s,&}]+)"
        ),
        r"\1***",
    ),
    (re.compile(r"(?i)(x-api-key\s*:\s*)(\S+)"), r"\1***"),
    (re.compile(r"(https?://)([^/@\s:]+):([^/@\s@]+)@(\S+)"), r"\1***:***@\4"),
)

_trace_id: ContextVar[str] = ContextVar("trace_id", default="-")
_request_id: ContextVar[str] = ContextVar("request_id", default="-")

_logger_lock = threading.Lock()
_metrics_lock = threading.Lock()
_counters: dict[str, int] = {}
_durations_ms: dict[str, list[float]] = {}


def new_trace_id() -> str:
    """Create a fresh trace id and bind it to the current context."""
    value = uuid.uuid4().hex[:16]
    _trace_id.set(value)
    return value


def new_request_id() -> str:
    """Create a fresh request id (separate from the trace for fan-out calls)."""
    value = uuid.uuid4().hex[:12]
    _request_id.set(value)
    return value


def current_trace_id() -> str:
    """Return the trace id bound to the current context."""
    return _trace_id.get()


def redact(message: str) -> str:
    """Mask obvious secrets (API keys, tokens, basic-auth URLs) in free text."""
    for pattern, replacement in _SECRET_PATTERNS:
        message = pattern.sub(replacement, message)
    return message


def _redact_obj(value: Any) -> Any:
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if isinstance(key, str) and re.search(
                r"(?i)api[_-]?key|token|secret|password|authorization", key
            ):
                cleaned[key] = "***"
            else:
                cleaned[key] = _redact_obj(item)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [_redact_obj(item) for item in value]
    return value


class JsonLogger:
    """Minimal JSON-lines logger with bound context and redaction."""

    def __init__(self, environment: str = "production") -> None:
        self.environment = environment

    def _emit(self, level: str, event: str, **fields: Any) -> None:
        record = {
            "ts": round(time.time(), 3),
            "level": level,
            "event": event,
            "service": "mcp-shlink",
            "environment": self.environment,
            "trace_id": _trace_id.get(),
            "request_id": _request_id.get(),
        }
        record.update(_redact_obj(fields))
        line = json.dumps(record, separators=(",", ":"), default=str)
        with _logger_lock:
            sys.stderr.write(line + "\n")
            sys.stderr.flush()

    def info(self, event: str, **fields: Any) -> None:
        self._emit("info", event, **fields)

    def warning(self, event: str, **fields: Any) -> None:
        self._emit("warning", event, **fields)

    def error(self, event: str, **fields: Any) -> None:
        self._emit("error", event, **fields)


_logger: JsonLogger | None = None


def get_logger(environment: str = "production") -> JsonLogger:
    """Return the process-wide logger, creating it on first use."""
    global _logger
    if _logger is None:
        _logger = JsonLogger(environment=environment)
    return _logger


def reset_logger() -> None:
    """Drop the cached logger (used by tests)."""
    global _logger
    _logger = None


def configure_logging(environment: str) -> JsonLogger:
    """Reset and configure the process-wide logger."""
    reset_logger()
    return get_logger(environment=environment)


@contextmanager
def traced(tool: str, logger: JsonLogger | None = None) -> Iterator[dict[str, Any]]:
    """Bind a trace id, time the block, and record duration/count metrics.

    Yields a dict that the caller may extend with extra log fields; on exit a
    ``tool.completed`` (or ``tool.failed``) event is logged with the elapsed ms.
    """
    new_trace_id()
    new_request_id()
    fields: dict[str, Any] = {"tool": tool}
    start = time.perf_counter()
    try:
        yield fields
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        observe_duration(f"tool.{tool}", elapsed_ms)
        increment_counter(f"tool.{tool}.errors")
        if logger is not None:
            logger.error(
                "tool.failed",
                duration_ms=round(elapsed_ms, 2),
                error_type=type(exc).__name__,
                **fields,
            )
        raise
    else:
        elapsed_ms = (time.perf_counter() - start) * 1000
        observe_duration(f"tool.{tool}", elapsed_ms)
        increment_counter(f"tool.{tool}.calls")
        if logger is not None:
            logger.info("tool.completed", duration_ms=round(elapsed_ms, 2), **fields)


def increment_counter(name: str, amount: int = 1) -> None:
    """Increment an in-process counter."""
    with _metrics_lock:
        _counters[name] = _counters.get(name, 0) + amount


def observe_duration(name: str, duration_ms: float) -> None:
    """Record one duration sample (milliseconds) for the named operation."""
    with _metrics_lock:
        _durations_ms.setdefault(name, []).append(duration_ms)


def snapshot_metrics() -> dict[str, Any]:
    """Return counters and duration stats (count/mean/p95/max) for dumping."""
    with _metrics_lock:
        counters = dict(_counters)
        durations = {name: list(samples) for name, samples in _durations_ms.items()}

    stats: dict[str, Any] = {"counters": counters, "durations_ms": {}}
    for name, samples in durations.items():
        ordered = sorted(samples)
        count = len(ordered)
        p95_index = min(count - 1, int(round(0.95 * (count - 1))))
        stats["durations_ms"][name] = {
            "count": count,
            "mean": round(sum(ordered) / count, 2) if count else 0.0,
            "p95": round(ordered[p95_index], 2) if count else 0.0,
            "max": round(ordered[-1], 2) if count else 0.0,
        }
    return stats


def reset_metrics() -> None:
    """Clear all recorded metrics (used by tests)."""
    with _metrics_lock:
        _counters.clear()
        _durations_ms.clear()
