"""Unit tests for typed configuration loading."""

from __future__ import annotations

import pytest

from mcp_shlink.config import (
    ConfigurationError,
    Settings,
    as_env_dict,
    load_settings,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "SHLINK_BASE_URL",
        "SHLINK_API_KEY",
        "SHLINK_ENV",
        "SHLINK_ANALYTICS_ENABLED",
        "SHLINK_ANALYTICS_ENDPOINT",
        "SENTRY_DSN",
    ):
        monkeypatch.delenv(name, raising=False)


class TestLoadSettings:
    def test_missing_required_vars_raise(self):
        with pytest.raises(ConfigurationError, match="SHLINK_BASE_URL and SHLINK_API_KEY"):
            load_settings()

    def test_missing_api_key_raises(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("SHLINK_BASE_URL", "https://shlink.example.com")
        with pytest.raises(ConfigurationError):
            load_settings()

    def test_empty_string_treated_as_unset(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("SHLINK_BASE_URL", "   ")
        monkeypatch.setenv("SHLINK_API_KEY", "key")
        with pytest.raises(ConfigurationError):
            load_settings()

    def test_valid_config_loads(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("SHLINK_BASE_URL", "https://shlink.example.com")
        monkeypatch.setenv("SHLINK_API_KEY", "changeme")
        monkeypatch.setenv("SHLINK_ENV", "staging")

        settings = load_settings()

        assert settings.base_url == "https://shlink.example.com"
        assert settings.api_key == "changeme"
        assert settings.shlink_env == "staging"
        assert settings.analytics_enabled is False

    def test_bool_parsing_variants(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("SHLINK_BASE_URL", "https://s.example.com")
        monkeypatch.setenv("SHLINK_API_KEY", "k")
        for raw, expected in (
            ("1", True),
            ("true", True),
            ("YES", True),
            ("on", True),
            ("0", False),
        ):
            monkeypatch.setenv("SHLINK_ANALYTICS_ENABLED", raw)
            assert load_settings().analytics_enabled is expected

    def test_settings_are_frozen(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("SHLINK_BASE_URL", "https://s.example.com")
        monkeypatch.setenv("SHLINK_API_KEY", "k")
        settings = load_settings()
        with pytest.raises(Exception):
            settings.api_key = "rotated"  # type: ignore[misc]


class TestAsEnvDict:
    def test_api_key_never_leaks_into_dict(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("SHLINK_BASE_URL", "https://s.example.com")
        monkeypatch.setenv("SHLINK_API_KEY", "changeme")
        dumped = as_env_dict(load_settings())
        assert "api_key" not in dumped
        assert dumped["base_url"] == "https://s.example.com"

    def test_none_fields_excluded(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("SHLINK_BASE_URL", "https://s.example.com")
        monkeypatch.setenv("SHLINK_API_KEY", "k")
        dumped = as_env_dict(load_settings())
        assert "sentry_dsn" not in dumped

    def test_settings_model_defaults(self):
        settings = Settings(base_url="https://x", api_key="k")
        assert settings.shlink_env == "production"
        assert settings.analytics_enabled is False
        assert settings.analytics_endpoint is None
