from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from core.db import DatabaseManager
from core.auth import AuthManager

logger = logging.getLogger(__name__)

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche le tableau de bord avec les boutons interactifs"""
    user_id = str(update.effective_user.id)
    auth = AuthManager()
    user = auth.get_user(user_id)
    
    if not user or user[2] not in ['super_admin', 'president', 'tresorier']:
        await update.message.reply_text("⛔ Vous n'avez pas l'autorisation d'accéder au Dashboard.")
        return

    db = DatabaseManager()
    success, stats = db.get_dashboard_stats()
    db.close()

    if not success:
        await update.message.reply_text("❌ Erreur lors de la récupération des statistiques.")
        return

    text = (
        "📊 *DASHBOARD YESSAL ASSO* 📊\n\n"
        f"👥 *Contacts totaux :* {stats.get('total_contacts', 0)}\n"
        f"🏷️ *Adhérents :* {stats.get('active_members', 0)} actifs / {stats.get('total_members', 0)} totaux\n"
        f"💰 *Cotisations collectées :* {stats.get('total_contributions', 0):,.0f} FCFA\n\n"
        "Que souhaitez-vous faire ?"
    )

    keyboard = [
        [InlineKeyboardButton("🔄 Sync Contacts", callback_data="action_sync_contacts"),
         InlineKeyboardButton("🔄 Sync Membres", callback_data="action_sync_members")],
        [InlineKeyboardButton("🔄 Sync Adhésions", callback_data="action_sync_memberships"),
         InlineKeyboardButton("🔄 Sync Cotisations", callback_data="action_sync_contributions")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les clics sur les boutons inline"""
    query = update.callback_query
    await query.answer()

    if query.data == "action_sync_contacts":
        await query.edit_message_text(text="Veuillez utiliser la commande /sync pour lancer la synchronisation.")
    elif query.data == "action_sync_members":
        await query.edit_message_text(text="Veuillez utiliser la commande /sync_members.")
    elif query.data == "action_sync_memberships":
        await query.edit_message_text(text="Veuillez utiliser la commande /sync_memberships.")
    elif query.data == "action_sync_contributions":
        await query.edit_message_text(text="Veuillez utiliser la commande /sync_contributions.")