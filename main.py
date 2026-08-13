import os
import logging
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

from core.db import DatabaseManager
from services.dolibarr_api import DolibarrClient
from modules.contacts import sync_contacts_command, search_contact_command
from modules.members import sync_members_command, search_member_command
from modules.memberships import sync_memberships_command
from modules.contributions import sync_contributions_command
from modules.dashboard import dashboard_command, button_callback
from modules.jobs import background_sync_job
from modules.report import weekly_report_command

load_dotenv()
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')

async def start(update, context):
    await update.message.reply_text("👋 Bienvenue sur Yessal Asso Bot !")

async def init_db_command(update, context):
    db = DatabaseManager()
    _, msg = db.init_db()
    db.close()
    await update.message.reply_text(msg)

async def ping_dolibarr_command(update, context):
    client = DolibarrClient()
    _, msg = client.ping()
    await update.message.reply_text(msg)

if __name__ == '__main__':
    if not TELEGRAM_TOKEN:
        print("Erreur token")
        exit(1)

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
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(CommandHandler("report", weekly_report_command))

    print("Yessal Asso Bot démarré...")
    
    # Configuration de la JobQueue pour les tâches en arrière-plan
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(background_sync_job, interval=21600, first=10)
        logger.info("⏰ JobQueue configurée : Synchronisation automatique active.")
    else:
        logger.warning("⚠️ JobQueue non disponible. Les tâches planifiées sont désactivées.")
    
    app.run_polling()
