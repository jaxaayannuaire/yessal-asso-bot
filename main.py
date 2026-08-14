import logging
import os

from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler

from core.db import DatabaseManager
from services.dolibarr_api import DolibarrClient
from modules.contacts import search_contact_command, sync_contacts_command
from modules.members import search_member_command, sync_members_command
from modules.memberships import sync_memberships_command
from modules.contributions import sync_contributions_command
from modules.dashboard import button_callback, dashboard_command
from modules.jobs import background_sync_job, scheduled_weekly_report
from modules.report import test_alert_command, weekly_report_command
from modules.cash import caisse_command, cash_callback, entree_command, sortie_command
from modules.roles import (
    create_roles_command,
    link_me_command,
    nommer_admin_command,
    nommer_bureau_command,
    nommer_membre_command,
    nommer_president_command,
    nommer_tresorier_command,
    refresh_command_menu,
    roles_command,
    sync_roles_command,
)

load_dotenv()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
)
logger = logging.getLogger(__name__)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")


async def start(update, context):
    await refresh_command_menu(context.bot, update.effective_user.id)
    await update.message.reply_text(
        "👋 Bienvenue sur *Yessal Asso Bot*.\n\n"
        "Les commandes affichées dans votre menu dépendent de vos droits.\n"
        "Les contrôles d'accès sont également appliqués à chaque commande.",
        parse_mode="Markdown",
    )


async def init_db_command(update, context):
    db = DatabaseManager()
    try:
        _, msg = db.init_db()
    finally:
        db.close()
    await update.message.reply_text(msg)


async def ping_dolibarr_command(update, context):
    client = DolibarrClient()
    _, msg = client.ping()
    await update.message.reply_text(msg)


def build_application():
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN / TELEGRAM_BOT_TOKEN manquant dans .env")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("init_db", init_db_command))
    app.add_handler(CommandHandler("ping_dolibarr", ping_dolibarr_command))
    app.add_handler(CommandHandler("sync", sync_contacts_command))
    app.add_handler(CommandHandler("contact", search_contact_command))
    app.add_handler(CommandHandler("sync_members", sync_members_command))
    app.add_handler(CommandHandler("membre", search_member_command))
    app.add_handler(CommandHandler("sync_memberships", sync_memberships_command))
    app.add_handler(CommandHandler("sync_contributions", sync_contributions_command))
    app.add_handler(CommandHandler("dashboard", dashboard_command))
    app.add_handler(CommandHandler("caisse", caisse_command))
    app.add_handler(CommandHandler("entree", entree_command))
    app.add_handler(CommandHandler("sortie", sortie_command))
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"^action_"))
    app.add_handler(CallbackQueryHandler(cash_callback, pattern=r"^cash_"))
    app.add_handler(CommandHandler("report", weekly_report_command))
    app.add_handler(CommandHandler("test_alert", test_alert_command))

    app.add_handler(CommandHandler("roles", roles_command))
    app.add_handler(CommandHandler("sync_roles", sync_roles_command))
    app.add_handler(CommandHandler("creer_groupes", create_roles_command))
    app.add_handler(CommandHandler("lier_moi", link_me_command))
    app.add_handler(CommandHandler("nommer_tresorier", nommer_tresorier_command))
    app.add_handler(CommandHandler("nommer_president", nommer_president_command))
    app.add_handler(CommandHandler("nommer_bureau", nommer_bureau_command))
    app.add_handler(CommandHandler("nommer_admin", nommer_admin_command))
    app.add_handler(CommandHandler("nommer_membre", nommer_membre_command))

    if app.job_queue:
        app.job_queue.run_repeating(background_sync_job, interval=21600, first=10)
        app.job_queue.run_repeating(scheduled_weekly_report, interval=604800, first=30)
        logger.info("JobQueue configurée : sync et rapport hebdomadaire actifs.")
    else:
        logger.warning("JobQueue indisponible : jobs automatiques désactivés.")
    return app


if __name__ == "__main__":
    logger.info("Yessal Asso Bot démarré...")
    build_application().run_polling()
