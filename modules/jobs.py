import logging
from telegram.ext import ContextTypes
from services.dolibarr_api import DolibarrClient
from core.db import DatabaseManager
import os

logger = logging.getLogger(__name__)

async def background_sync_job(context: ContextTypes.DEFAULT_TYPE):
    """Job automatique : Synchronise en arrière-plan les contacts et membres depuis Dolibarr"""
    logger.info("⏳ Lancement du job de synchronisation automatique...")
    client = DolibarrClient()
    db = DatabaseManager()
    try:
        success_c, data_c = client.get_contacts()
        if success_c:
            db.sync_contacts(data_c)
            
        success_m, data_m = client.get_members()
        if success_m:
            db.sync_members(data_m)
        logger.info("✅ Job auto de synchronisation terminé.")
    except Exception as e:
        logger.error(f"❌ Erreur background_sync_job : {e}")
    finally:
        db.close()

async def scheduled_weekly_report(context: ContextTypes.DEFAULT_TYPE):
    """Job planifié : Envoie le rapport hebdomadaire dans le canal/groupe configuré"""
    logger.info("📊 Génération du rapport hebdomadaire automatique...")
    
    chat_id = os.getenv('ADMIN_CHAT_ID') # ID du groupe ou de l'admin configuré dans .env
    if not chat_id:
        logger.warning("⚠️ ADMIN_CHAT_ID non défini dans .env, impossible d'envoyer le rapport planifié.")
        return

    db = DatabaseManager()
    success, data = db.get_weekly_report_data()
    db.close()

    if not success:
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
        await context.bot.send_message(chat_id=chat_id, text=report_text, parse_mode='Markdown')
        logger.info("✅ Rapport hebdomadaire automatique envoyé avec succès.")
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'envoi du rapport automatique : {e}")