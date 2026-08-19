import inspect
import logging
import os
from dataclasses import dataclass

from services.dolibarr_api import DolibarrClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrganizationProfile:
    name: str
    logo: str | None = None


def get_organization_profile() -> OrganizationProfile:
    name = os.getenv("DOLIBARR_COMPANY_NAME", "").strip() or "YESSAL ASSO"
    logo = os.getenv("DOLIBARR_COMPANY_LOGO_URL", "").strip() or None
    return OrganizationProfile(name=name, logo=logo)


def build_page_header(title: str, profile: OrganizationProfile | None = None) -> str:
    profile = profile or get_organization_profile()
    return f"🏛️ *{profile.name}*\n\n*{title}*"


async def _await_if_needed(value):
    if inspect.isawaitable(value):
        return await value
    return value


async def send_page_header(update, context, title: str) -> None:
    """Envoie l'en-tête sans casser les environnements de test synchrones."""
    profile = get_organization_profile()
    message = update.effective_message

    if profile.logo:
        try:
            result = context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=profile.logo,
                caption=f"🏛️ *{profile.name}*",
                parse_mode="Markdown",
            )
            await _await_if_needed(result)
            return
        except Exception as exc:
            logger.warning("Envoi du logo impossible : %s", exc)

    result = message.reply_text(
        build_page_header(title, profile),
        parse_mode="Markdown",
    )
    await _await_if_needed(result)
