import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from modules.search import build_member_filters_keyboard, build_member_filters_text, recherche_member_filters


def test_member_filters_include_expected_fields():
    text = build_member_filters_text()
    for label in ("Nom", "Prénom", "Téléphone", "WhatsApp", "Ville",
                  "Sexe", "Mois d’adhésion", "Année d’adhésion",
                  "Fonction", "Responsabilité", "Tag / catégorie"):
        assert label in text


def test_member_filters_keyboard_has_search_and_reset():
    markup = build_member_filters_keyboard()
    labels = [button.text for row in markup.inline_keyboard for button in row]
    assert "🔎 Rechercher" in labels
    assert "🧹 Réinitialiser" in labels
    assert "⬅️ Retour" in labels


@pytest.mark.asyncio
async def test_member_filter_callback_displays_form():
    update = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.data = "search:type:members"
    context = MagicMock()
    context.user_data = {}
    with patch("modules.search.AuthManager"):
        await recherche_member_filters(update, context)
    kwargs = update.callback_query.edit_message_text.await_args.kwargs
    assert "RECHERCHE ADHÉRENT" in kwargs["text"]
    assert kwargs["reply_markup"] is not None
