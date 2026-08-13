import logging
import os

from telegram.ext import ContextTypes

from core.db import DatabaseManager
from services.dolibarr_api import DolibarrClient

logger = logging.getLogger(__name__)


async def background_sync_job(context: ContextTypes.DEFAULT_TYPE):
    """Synchronise automatiquement les contacts et adhérents depuis Dolibarr."""
    logger.info("Lancement du job de synchronisation automatique")
    client = DolibarrClient()
    db = DatabaseManager()
    try:
        success_contacts, contacts = client.get_contacts()
        if success_contacts:
            db.sync_contacts(contacts)
        else:
            logger.warning("Sync contacts échouée : %s", contacts)

        success_members, members = client.get_members()
        if success_members:
            db.sync_members(members)
        else:
            logger.warning("Sync membres échouée : %s", members)

        logger.info("Job de synchronisation automatique terminé")
    except Exception:
        logger.exception("Erreur background_sync_job")
    finally:
        db.close()


async def scheduled_weekly_report(context: ContextTypes.DEFAULT_TYPE):
    """Envoie le rapport hebdomadaire dans le chat administratif configuré."""
    chat_id = os.getenv("ADMIN_CHAT_ID") or os.getenv("TELEGRAM_MAIN_GROUP_ID")
    if not chat_id:
        logger.warning("ADMIN_CHAT_ID / TELEGRAM_MAIN_GROUP_ID non défini")
        return

    db = DatabaseManager()
    try:
        success, data = db.get_weekly_report_data()
    finally:
        db.close()

    if not success:
        logger.error("Impossible de générer le rapport hebdomadaire")
        return

    report_text = f"""📊 *RAPPORT HEBDOMADAIRE AUTOMATIQUE - YESSAL ASSO* 📊

👥 *Membres & Adhérents :*
- Total enregistrés : {data.get('total_members', 0)}
- Adhérents actifs : {data.get('active_members', 0)}

💰 *Cotisations & Finances :*
- Nombre de versements : {data.get('total_cotisations_count', 0)}
- Montant total collecté : *{data.get('total_cotisations_amount', 0):,.0f} FCFA*

_Envoyé automatiquement par Yessal Asso Bot._
"""
    try:
        await context.bot.send_message(chat_id=chat_id, text=report_text, parse_mode="Markdown")
        logger.info("Rapport hebdomadaire envoyé")
    except Exception:
        logger.exception("Erreur lors de l'envoi du rapport hebdomadaire")
