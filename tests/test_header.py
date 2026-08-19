from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.header import OrganizationProfile, build_page_header, get_organization_profile, send_page_header


def test_build_page_header_contains_reason_sociale_and_title():
    text = build_page_header(
        "RÉSULTATS ADHÉRENTS",
        OrganizationProfile("Association Test"),
    )
    assert "Association Test" in text
    assert "RÉSULTATS ADHÉRENTS" in text


def test_get_organization_profile_uses_env_fallback(monkeypatch):
    monkeypatch.setenv("DOLIBARR_COMPANY_NAME", "Association Yessal")
    monkeypatch.setenv("DOLIBARR_COMPANY_LOGO_URL", "https://example.test/logo.png")

    with patch("core.header.DolibarrClient") as client_cls:
        client_cls.return_value.get_organization_info = MagicMock(
            return_value=(False, "indisponible")
        )
        profile = get_organization_profile()

    assert profile.name == "Association Yessal"
    assert profile.logo == "https://example.test/logo.png"


@pytest.mark.asyncio
async def test_send_page_header_sends_logo_when_available():
    update = MagicMock()
    update.effective_chat.id = 123
    update.effective_message.reply_text = AsyncMock()

    context = MagicMock()
    context.bot.send_photo = AsyncMock()

    with patch(
        "core.header.get_organization_profile",
        return_value=OrganizationProfile("Association Test", "https://example.test/logo.png"),
    ):
        await send_page_header(update, context, "RECHERCHE")

    context.bot.send_photo.assert_awaited_once()
    update.effective_message.reply_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_page_header_falls_back_to_text_without_logo():
    update = MagicMock()
    update.effective_message.reply_text = AsyncMock()

    context = MagicMock()
    context.bot.send_photo = AsyncMock()

    with patch(
        "core.header.get_organization_profile",
        return_value=OrganizationProfile("Association Test"),
    ):
        await send_page_header(update, context, "RECHERCHE")

    update.effective_message.reply_text.assert_awaited_once()
