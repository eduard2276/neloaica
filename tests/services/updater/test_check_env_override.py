"""Tests for the ``NELOAICA_UPDATE_MANIFEST_URL`` override.

Added in PR #8 so unreleased builds can be pointed at a manifest
hosted on a feature branch / staging server during testing.
"""

from __future__ import annotations

from src.services.updater import (
    BUILTIN_MANIFEST_URL,
    MANIFEST_URL_ENV_VAR,
    UpdateChecker,
    Version,
    default_manifest_url,
)

# ===========================================================================
# TestDefaultManifestUrl
# ===========================================================================


class TestDefaultManifestUrl:
    def test_returns_builtin_when_env_missing(self, monkeypatch):
        monkeypatch.delenv(MANIFEST_URL_ENV_VAR, raising=False)
        assert default_manifest_url() == BUILTIN_MANIFEST_URL

    def test_returns_env_value_when_set(self, monkeypatch):
        monkeypatch.setenv(MANIFEST_URL_ENV_VAR, "https://example.com/m.json")
        assert default_manifest_url() == "https://example.com/m.json"

    def test_empty_env_value_falls_back(self, monkeypatch):
        monkeypatch.setenv(MANIFEST_URL_ENV_VAR, "")
        assert default_manifest_url() == BUILTIN_MANIFEST_URL

    def test_whitespace_env_value_falls_back(self, monkeypatch):
        monkeypatch.setenv(MANIFEST_URL_ENV_VAR, "   ")
        assert default_manifest_url() == BUILTIN_MANIFEST_URL

    def test_strips_whitespace_around_env_value(self, monkeypatch):
        monkeypatch.setenv(MANIFEST_URL_ENV_VAR, "  https://x.example/m.json  ")
        assert default_manifest_url() == "https://x.example/m.json"


# ===========================================================================
# TestUpdateCheckerHonorsEnv
# ===========================================================================


class TestUpdateCheckerHonorsEnv:
    def test_checker_uses_env_when_no_url_passed(self, monkeypatch):
        monkeypatch.setenv(MANIFEST_URL_ENV_VAR, "https://feature-branch.example/m.json")
        checker = UpdateChecker(Version(1, 0, 0))
        assert checker.manifest_url == "https://feature-branch.example/m.json"

    def test_explicit_url_wins_over_env(self, monkeypatch):
        monkeypatch.setenv(MANIFEST_URL_ENV_VAR, "https://from-env.example/m.json")
        checker = UpdateChecker(Version(1, 0, 0), manifest_url="https://explicit.example/m.json")
        assert checker.manifest_url == "https://explicit.example/m.json"

    def test_default_url_used_when_env_absent(self, monkeypatch):
        monkeypatch.delenv(MANIFEST_URL_ENV_VAR, raising=False)
        checker = UpdateChecker(Version(1, 0, 0))
        assert checker.manifest_url == BUILTIN_MANIFEST_URL


# ===========================================================================
# TestBackwardCompatibility
# ===========================================================================


class TestBackwardCompatibility:
    def test_default_manifest_url_constant_still_exposed(self):
        # Older code imported the constant. We keep it exposed so
        # nothing breaks, but it does NOT honour the env var (callers
        # who want that should use ``default_manifest_url()``).
        from src.services.updater import DEFAULT_MANIFEST_URL

        assert DEFAULT_MANIFEST_URL == BUILTIN_MANIFEST_URL

    def test_constant_is_independent_of_env(self, monkeypatch):
        from src.services.updater import DEFAULT_MANIFEST_URL

        monkeypatch.setenv(MANIFEST_URL_ENV_VAR, "https://x/y.json")
        # The constant is a snapshot of the builtin at import time.
        assert DEFAULT_MANIFEST_URL == BUILTIN_MANIFEST_URL
