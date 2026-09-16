"""Typed, validated configuration for the MCP server.

All environment access flows through :func:`load_settings` so that required
variables stay documented in one place and fail fast with a clear error.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Settings(BaseModel):
    """Runtime configuration loaded from the environment."""

    model_config = ConfigDict(frozen=True)

    base_url: str = Field(description="Shlink instance base URL")
    api_key: str = Field(description="Shlink API key")
    shlink_env: str = Field(default="production", description="Deployment environment name")
    analytics_enabled: bool = Field(default=False, description="Opt-in anonymous tool usage events")
    analytics_endpoint: str | None = Field(
        default=None, description="Optional HTTP endpoint for events"
    )
    sentry_dsn: str | None = Field(default=None, description="Opt-in Sentry DSN for error tracking")


class ConfigurationError(RuntimeError):
    """Raised when required configuration is missing or malformed."""


def _get_env(name: str) -> str | None:
    """Read one environment variable, treating empty strings as unset."""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return None
    return value


def _get_bool(name: str, default: bool) -> bool:
    raw = _get_env(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    """Build :class:`Settings` from environment variables.

    Raises:
        ConfigurationError: If ``SHLINK_BASE_URL`` or ``SHLINK_API_KEY`` is unset.
    """
    base_url = _get_env("SHLINK_BASE_URL")
    api_key = _get_env("SHLINK_API_KEY")
    if not base_url or not api_key:
        raise ConfigurationError(
            "SHLINK_BASE_URL and SHLINK_API_KEY must be set (see README > Configuration)"
        )
    return Settings(
        base_url=base_url,
        api_key=api_key,
        shlink_env=_get_env("SHLINK_ENV") or "production",
        analytics_enabled=_get_bool("SHLINK_ANALYTICS_ENABLED", default=False),
        analytics_endpoint=_get_env("SHLINK_ANALYTICS_ENDPOINT"),
        sentry_dsn=_get_env("SENTRY_DSN"),
    )


@lru_cache(maxsize=1)
def cached_settings() -> Settings:
    """Cached variant used by long-lived code paths; tests use ``load_settings``."""
    return load_settings()


def as_env_dict(settings: Settings) -> dict[str, Any]:
    """Return the settings as a plain dict (never logs the API key)."""
    return settings.model_dump(exclude={"api_key"}, exclude_none=True)
