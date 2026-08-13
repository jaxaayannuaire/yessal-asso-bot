from telegram import Update
from telegram.ext import ContextTypes
import logging

from core.db import DatabaseManager
from core.auth import AuthManager, BOARD_ROLES
from modules.jobs import scheduled_weekly_report

logger = logging.getLogger(__name__)

async def weekly_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /report : Affiche le rapport hebdomadaire de l'association"""
    user_id = str(update.effective_user.id)
    auth = AuthManager()
    user = auth.get_user(user_id)
    
    # Seuls les admins, présidents et trésoriers peuvent consulter le rapport stratégique
    if not user or user[2] not in BOARD_ROLES:
        await update.message.reply_text("⛔ Accès réservé au Bureau de l'association.")
        return

    db = DatabaseManager()
    success, data = db.get_weekly_report_data()
    db.close()

    if not success:
        await update.message.reply_text("❌ Erreur lors de la génération du rapport.")
        return

    report_text = f"""📊 *RAPPORT HEBDOMADAIRE - YESSAL ASSO* 📊

👥 *Membres & Adhérents :*
- Total enregistrés : {data.get('total_members', 0)}
- Adhérents actifs : {data.get('active_members', 0)}

💰 *Cotisations & Finances :*
- Nombre de versements : {data.get('total_cotisations_count', 0)}
- Montant total collecté : *{data.get('total_cotisations_amount', 0):,.0f} FCFA*

_Généré automatiquement depuis le cache local DuckDB._
"""
    await update.message.reply_text(report_text, parse_mode='Markdown')
    
async def test_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /test_alert : Déclenche manuellement l'alerte/rapport hebdomadaire"""
    user_id = str(update.effective_user.id)
    auth = AuthManager()
    user = auth.get_user(user_id)
    
    # Vérification des rôles (Admin / Bureau uniquement)
    if not user or user[2] not in BOARD_ROLES:
        await update.message.reply_text("⛔ Accès réservé aux administrateurs.")
        return

    await update.message.reply_text("🚀 Déclenchement manuel de l'alerte en cours...")
    
    # Réutilise la fonction de rapport planifié en lui passant le contexte actuel
    try:
        await scheduled_weekly_report(context)
        await update.message.reply_text("✅ Alerte déclenchée et envoyée avec succès !")
    except Exception as e:
        logger.error(f"Erreur lors du test manuel de l'alerte : {e}")
        await update.message.reply_text(f"❌ Erreur : {e}")