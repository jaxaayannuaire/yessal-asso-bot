import logging
from telegram.ext import ContextTypes
from services.dolibarr_api import DolibarrClient
from core.db import DatabaseManager
import os

logger = logging.getLogger(__name__)

async def background_sync_job(context: ContextTypes.DEFAULT_TYPE):
    """Job automatique : Synchronise en arriÃ¨re-plan les contacts et membres depuis Dolibarr"""
    logger.info("â³ Lancement du job de synchronisation automatique...")
    client = DolibarrClient()
    db = DatabaseManager()
    try:
        success_c, data_c = client.get_contacts()
        if success_c:
            db.sync_contacts(data_c)
            
        success_m, data_m = client.get_members()
        if success_m:
            db.sync_members(data_m)
        logger.info("âœ… Job auto de synchronisation terminÃ©.")
    except Exception as e:
        logger.error(f"âŒ Erreur background_sync_job : {e}")
    finally:
        db.close()

async def scheduled_weekly_report(context: ContextTypes.DEFAULT_TYPE):
    """Job planifiÃ© : Envoie le rapport hebdomadaire dans le canal/groupe configurÃ©"""
    logger.info("ðŸ“Š GÃ©nÃ©ration du rapport hebdomadaire automatique...")
    
    chat_id = os.getenv('ADMIN_CHAT_ID')
    if not chat_id:
        logger.warning("âš ï¸ ADMIN_CHAT_ID non dÃ©fini dans .env")
        return

    db = DatabaseManager()
    success, data = db.get_weekly_report_data()
    db.close()

    if not success:
        return

    report_text = f"""ðŸ“Š *RAPPORT HEBDOMADAIRE AUTOMATIQUE - YESSAL ASSO* ðŸ“Š

ðŸ‘¥ *Membres & AdhÃ©rents :*
- Total enregistrÃ©s : {data.get('total_members', 0)}
- AdhÃ©rents actifs : {data.get('active_members', 0)}

ðŸ’° *Cotisations & Finances :*
- Nombre de versements : {data.get('total_cotisations_count', 0)}
- Montant total collectÃ© : *{data.get('total_cotisations_amount', 0):,.0f} FCFA*

_EnvoyÃ© automatiquement par Yessal Asso Bot._
"""
    try:
        await context.bot.send_message(chat_id=chat_id, text=report_text, parse_mode='Markdown')
        logger.info("âœ… Rapport hebdomadaire automatique envoyÃ© avec succÃ¨s.")
    except Exception as e:
        logger.error(f"âŒ Erreur lors de l'envoi du rapport automatique : {e}")

async def test_alert_command(update, context):
    """Commande /test_alert : DÃ©clenche manuellement l'alerte/rapport hebdomadaire"""
    user_id = str(update.effective_user.id)
    from core.auth import AuthManager
    auth = AuthManager()
    user = auth.get_user(user_id)
    
    if not user or user[2] not in ['super_admin', 'president', 'tresorier']:
        await update.message.reply_text("â›” AccÃ¨s rÃ©servÃ© aux administrateurs.")
        return

    await update.message.reply_text("ðŸš€ DÃ©clenchement manuel de l'alerte en cours...")
    try:
        await scheduled_weekly_report(context)
        await update.message.reply_text("âœ… Alerte dÃ©clenchÃ©e et envoyÃ©e avec succÃ¨s !")
    except Exception as e:
        await update.message.reply_text(f"âŒ Erreur : {e}")
