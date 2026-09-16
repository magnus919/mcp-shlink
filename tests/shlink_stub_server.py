"""A tiny local Shlink API stub for integration tests and local development.

Run it with::

    SHLINK_API_KEY=changeme python -m tests.shlink_stub_server --port 8765

It implements just enough of the Shlink REST v3 surface (create / list / get /
delete short URLs, tags) for the MCP server's tools and the integration test
suite, so tests and interactive QA never need a real Shlink deployment.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_STORE_LOCK = threading.Lock()
_STORE: dict[str, dict] = {}
_TAGS: dict[str, int] = {}


def _reset_store() -> None:
    """Clear all stub state (used between tests)."""
    with _STORE_LOCK:
        _STORE.clear()
        _TAGS.clear()


def _record_to_json(record: dict) -> dict:
    return {
        "shortUrl": record["shortUrl"],
        "shortCode": record["shortCode"],
        "longUrl": record["longUrl"],
        "dateCreated": record["dateCreated"],
        "tags": record["tags"],
        "visitsCount": record["visitsCount"],
        "visitsSummary": {"total": record["visitsCount"]},
    }


class ShlinkStubHandler(BaseHTTPRequestHandler):
    """Minimal Shlink REST v3-compatible request handler."""

    server_version = "ShlinkStub/1.0"

    # -- helpers ---------------------------------------------------------
    def _json_body(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        expected = os.environ.get("SHLINK_API_KEY", "changeme")
        return self.headers.get("X-Api-Key") == expected

    def _segments(self) -> list[str]:
        return [segment for segment in self.path.split("?")[0].split("/") if segment]

    def _guard(self, resource: str, prefix_len: int, exact_len: int | None = None) -> bool:
        """Shared auth + route guard for POST/DELETE handlers.

        Returns True when the request may proceed; otherwise the error response
        has already been sent.
        """
        if not self._authorized():
            self._json_body(401, {"error": "unauthorized"})
            return False
        segments = self._segments()
        if segments[:prefix_len] != ["rest", "v3", resource]:
            self._json_body(404, {"error": "not found"})
            return False
        if exact_len is not None and len(segments) != exact_len:
            self._json_body(404, {"error": "not found"})
            return False
        return True

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib API
        # Keep test output quiet; errors still surface via status codes.
        return

    # -- verbs -----------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802 - stdlib API
        if not self._authorized():
            self._json_body(401, {"error": "unauthorized"})
            return
        segments = self._segments()
        if segments[:2] != ["rest", "v3"]:
            self._json_body(404, {"error": "not found"})
            return
        resource = segments[2] if len(segments) > 2 else ""

        if resource == "short-urls" and len(segments) == 3:
            with _STORE_LOCK:
                records = list(_STORE.values())
            self._json_body(
                200,
                {
                    "shortUrls": {
                        "data": [_record_to_json(record) for record in records],
                        "pagination": {
                            "currentPage": 1,
                            "pageCount": 1,
                            "totalItems": len(records),
                        },
                    }
                },
            )
            return

        if resource == "short-urls" and len(segments) == 4:
            short_code = segments[3]
            with _STORE_LOCK:
                record = _STORE.get(short_code)
            if record is None:
                self._json_body(404, {"error": "not found"})
                return
            self._json_body(200, _record_to_json(record))
            return

        if resource == "tags":
            with _STORE_LOCK:
                tags = [
                    {"tag": tag, "shortUrlsCount": count} for tag, count in sorted(_TAGS.items())
                ]
            self._json_body(200, {"data": tags})
            return

        self._json_body(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 - stdlib API
        if not self._guard("short-urls", prefix_len=3):
            return
        length = int(self.headers.get("Content-Length") or 0)
        payload: dict = json.loads(self.rfile.read(length) or b"{}")
        short_code = payload.get("customSlug") or uuid.uuid4().hex[:6]
        base = f"http://{self.headers.get('Host', 'localhost')}"
        record = {
            "shortUrl": f"{base}/{short_code}",
            "shortCode": short_code,
            "longUrl": payload.get("longUrl", ""),
            "dateCreated": "2024-01-01T00:00:00+00:00",
            "tags": payload.get("tags", []),
            "visitsCount": 0,
        }
        with _STORE_LOCK:
            _STORE[short_code] = record
            for tag in record["tags"]:
                _TAGS[tag] = _TAGS.get(tag, 0) + 1
        self._json_body(201, _record_to_json(record))

    def do_DELETE(self) -> None:  # noqa: N802 - stdlib API
        if not self._guard("short-urls", prefix_len=3, exact_len=4):
            return
        short_code = self._segments()[3]
        with _STORE_LOCK:
            record = _STORE.pop(short_code, None)
            if record is not None:
                for tag in record["tags"]:
                    _TAGS[tag] = max(0, _TAGS.get(tag, 1) - 1)
                    if _TAGS[tag] == 0:
                        del _TAGS[tag]
        if record is None:
            self._json_body(404, {"error": "not found"})
            return
        self.send_response(204)
        self.end_headers()


@contextmanager
def running_stub(
    port: int = 0, api_key: str = "changeme"
) -> Iterator[tuple[str, ThreadingHTTPServer]]:
    """Start the stub on an ephemeral port and yield (base_url, server)."""
    server = ThreadingHTTPServer(("127.0.0.1", port), ShlinkStubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", server
    finally:
        server.shutdown()
        server.server_close()


def main() -> None:
    """Run the stub as a standalone process for interactive QA."""
    parser = argparse.ArgumentParser(description="Local Shlink API stub")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    os.environ.setdefault("SHLINK_API_KEY", "changeme")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), ShlinkStubHandler)
    print(f"Shlink stub listening on http://127.0.0.1:{args.port} (api key: changeme)")
    server.serve_forever()


if __name__ == "__main__":
    main()
