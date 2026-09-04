"""Settings must tolerate a deployed .env that is ahead of, or behind, the code."""

import pytest
from pydantic_settings import BaseSettings

from vahn_mcp.config import Settings


def test_retired_settings_do_not_prevent_startup(monkeypatch):
    """Removing a field must not break boxes whose .env still sets it.

    Dropping LSQ_ACCESS_KEY/LSQ_SECRET_KEY from Settings took production down:
    pydantic-settings forbids extra inputs by default, so the leftover lines in
    the deployed .env became a fatal ValidationError at import.
    """
    monkeypatch.setenv("LSQ_ACCESS_KEY", "leftover")
    monkeypatch.setenv("LSQ_SECRET_KEY", "leftover")
    monkeypatch.setenv("SOME_FUTURE_SETTING", "whatever")

    s = Settings()
    assert s.crm_service_url
    assert not hasattr(s, "lsq_access_key")


def test_known_settings_still_load(monkeypatch):
    monkeypatch.setenv("CRM_SERVICE_URL", "http://example.test:9999")
    monkeypatch.setenv("CRM_SERVICE_KEY", "abc123")
    s = Settings()
    assert s.crm_service_url == "http://example.test:9999"
    assert s.crm_service_key == "abc123"


def test_extra_is_ignored_not_forbidden():
    """Pin the setting itself — the default is forbid, and it is a boot failure."""
    assert Settings.model_config.get("extra") == "ignore"
