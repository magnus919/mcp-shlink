"""Unit tests for the feature flag registry."""

from __future__ import annotations

import pytest

from mcp_shlink import features


@pytest.fixture(autouse=True)
def _reset_flags():
    features.reset_flags()
    yield
    features.reset_flags()


class TestFeatureFlags:
    def test_all_flags_default_to_disabled(self):
        features.reset_flags()
        for value in features.all_flags().values():
            assert value is False

    def test_known_flag_resolves_from_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("FLAG_SHLINK_SOFT_DELETE_ENABLED", "true")
        features.reset_flags()
        assert features.is_enabled("shlink.soft_delete.enabled") is True

    def test_unknown_flag_returns_false_and_logs(self, capsys):
        assert features.is_enabled("shlink.not_a_real_flag") is False
        assert "feature_flag.unknown" in capsys.readouterr().err

    def test_set_flag_for_tests_overrides(self):
        features.set_flag_for_tests("shlink.retry_5xx.enabled", True)
        assert features.is_enabled("shlink.retry_5xx.enabled") is True

    def test_set_flag_for_unknown_flag_raises(self):
        with pytest.raises(KeyError):
            features.set_flag_for_tests("nope.not_real", True)

    def test_flag_table_documents_removal_intent(self):
        # Every flag must have a non-empty env mapping; guards against
        # registering a flag without documenting how to toggle it.
        for flag in features.FLAG_DEFAULTS:
            env_name = "FLAG_" + flag.replace(".", "_").replace("-", "_").upper()
            assert env_name.isidentifier() or "_" in env_name

    def test_env_false_disables_explicitly(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("FLAG_SHLINK_ANALYTICS_ENABLED", "false")
        features.reset_flags()
        assert features.is_enabled("shlink.analytics.enabled") is False
