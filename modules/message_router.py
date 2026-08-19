"""Routeur centralisé des messages texte Telegram."""

from modules.search import (
    handle_contact_filter_input,
    handle_member_filter_input,
)
from modules.member_wizard import wizard_text_router


async def message_text_router(update, context):
    """Route un message vers la recherche active ou le wizard."""
    if await handle_contact_filter_input(update, context):
        return
    if await handle_member_filter_input(update, context):
        return
    await wizard_text_router(update, context)
