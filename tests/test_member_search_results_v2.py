from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.search import build_member_filters_text, search_callback


def test_selected_member_filter_value_is_bold():
    text = build_member_filters_text({"lastname": "samb"})
    assert "Nom : *samb*" in text
    assert "Prénom : —" in text


@pytest.mark.asyncio
async def test_run_member_search_displays_results():
    update = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.data = "search:run:member"

    context = MagicMock()
    context.user_data = {"search_filters": {"lastname": "samb"}}

    with patch("modules.search._run_member_search", return_value=(
        True,
        [{
            "id": "1",
            "lastname": "SAMB",
            "firstname": "Pape",
            "ref": "A2604-0001",
            "phone": "770000000",
        }],
    )):
        await search_callback(update, context)

    kwargs = update.callback_query.edit_message_text.await_args.kwargs
    assert "RÉSULTATS ADHÉRENTS" in kwargs["text"]
    assert "SAMB Pape" in kwargs["text"]
