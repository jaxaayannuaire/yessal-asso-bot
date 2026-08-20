"""Routeur de recherche avec présentation détaillée des contacts."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import modules.search as search
from modules.contact_presentation import (
    build_contact_detail_text,
    get_contact_details,
    install_search_presentation,
)

install_search_presentation()


async def search_callback(update, context):
    data = (update.callback_query.data or "") if update.callback_query else ""

    if data.startswith("search:contact:view:"):
        query = update.callback_query
        contact_id = data.rsplit(":", 1)[-1]
        results = context.user_data.get(search.CONTACT_RESULTS_KEY, [])
        fallback = next(
            (item for item in results if str(item.get("id")) == contact_id),
            None,
        )

        await query.answer()
        if not fallback:
            await query.answer("Résultat introuvable.", show_alert=True)
            return

        success, contact = get_contact_details(contact_id, fallback=fallback)
        if not success or not isinstance(contact, dict):
            contact = fallback

        await query.edit_message_text(
            text=build_contact_detail_text(contact),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Résultats", callback_data="search:run:contact")]
            ]),
            parse_mode="Markdown",
        )
        return

    return await search.search_callback(update, context)
