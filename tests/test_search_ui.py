from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.search import (
    _build_keyboard,
    _build_search_text,
    recherche_command,
    search_callback,
)


def make_update(user_id="123"):
    update = MagicMock()
    update.effective_user.id = int(user_id)
    update.message.reply_text = AsyncMock()
    update.callback_query = AsyncMock()
    return update


def make_context():
    return MagicMock()


def test_search_text_contains_title_and_known_stats():
    text = _build_search_text(
        {
            "total_contacts": 100,
            "total_members": 10,
            "total_contributions": 50000,
        }
    )
    assert "RECHERCHE YESSAL ASSO" in text
    assert "Contacts" in text
    assert "100" in text
    assert "Adhérents" in text
    assert "10" in text
    assert "50 000 FCFA" in text


def test_keyboard_is_two_columns_and_has_close():
    markup = _build_keyboard(
        {"total_contacts": 100, "total_members": 10, "total_contributions": 50000}
    )
    assert all(len(row) == 2 for row in markup.inline_keyboard[:-1])
    assert len(markup.inline_keyboard[-1]) == 1
    assert markup.inline_keyboard[-1][0].callback_data == "search:close"


@pytest.mark.asyncio
async def test_search_command_denies_unauthorized_user():
    update = make_update()
    context = make_context()
    with patch("modules.search.AuthManager") as auth_cls:
        auth_cls.return_value.get_user.return_value = None
        await recherche_command(update, context)
    update.message.reply_text.assert_awaited_once_with("⛔ Accès refusé à la recherche.")


@pytest.mark.asyncio
async def test_search_command_displays_home():
    update = make_update()
    context = make_context()
    with patch("modules.search.AuthManager") as auth_cls, \
         patch("modules.search._get_search_stats", return_value={
             "total_contacts": 100,
             "total_members": 10,
             "total_contributions": 50000,
         }):
        auth_cls.return_value.get_user.return_value = ("123", "user", "president")
        await recherche_command(update, context)
    kwargs = update.message.reply_text.await_args.kwargs
    assert "RECHERCHE YESSAL ASSO" in kwargs["text"]
    assert kwargs["reply_markup"] is not None


@pytest.mark.asyncio
async def test_member_callback_shows_filters():
    update = make_update()
    update.callback_query.data = "search:type:members"
    context = make_context()
    await search_callback(update, context)
    text = update.callback_query.edit_message_text.await_args.kwargs["text"]
    assert "Recherche — Adhérents" in text
    assert "Nom" in text
    assert "Fonction" in text
