"""Shared pytest fixtures and guarantees for the mcp-shlink test suite.

Tests must never reach a real Shlink instance, so this module fails fast if
production-looking credentials are present in the environment.
"""

from __future__ import annotations

import pytest

_REAL_LOOKING_HOSTS = ("shlink.io", "shlink.example-prod")


@pytest.fixture(autouse=True, scope="session")
def _no_real_credentials() -> None:
    import os

    base_url = os.environ.get("SHLINK_BASE_URL", "")
    for host in _REAL_LOOKING_HOSTS:
        if host in base_url:
            pytest.exit(f"refusing to run tests against real host in SHLINK_BASE_URL: {host}")
