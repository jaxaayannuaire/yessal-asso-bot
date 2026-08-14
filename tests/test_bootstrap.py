import os

from modules.roles import _bootstrap_allowed


def test_bootstrap_requires_explicit_telegram_allowlist(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ADMIN_IDS", "12345,67890")
    assert _bootstrap_allowed("12345")
    assert _bootstrap_allowed("67890")
    assert not _bootstrap_allowed("99999")


def test_bootstrap_allowlist_supports_semicolon(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ADMIN_IDS", "12345;67890")
    assert _bootstrap_allowed("67890")
