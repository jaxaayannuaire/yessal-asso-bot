from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.db import DatabaseManager
from core.auth import AuthManager

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    auth = AuthManager()
    user = auth.get_user(user_id)
    if not user or user[2] not in ['super_admin', 'president', 'tresorier']:
        await update.message.reply_text("⛔ Accès refusé au Dashboard.")
        return

    db = DatabaseManager()
    success, stats = db.get_dashboard_stats()
    db.close()

    if not success:
        await update.message.reply_text("❌ Erreur stats.")
        return

    text = (
        "📊 *DASHBOARD YESSAL ASSO* 📊\n\n"
        f"👥 *Contacts :* {stats.get('total_contacts', 0)}\n"
        f"🏷️ *Adhérents :* {stats.get('active_members', 0)} actifs / {stats.get('total_members', 0)} totaux\n"
        f"💰 *Cotisations :* {stats.get('total_contributions', 0):,.0f} FCFA\n\n"
        "Actions rapides :"
    )

    keyboard = [
        [InlineKeyboardButton("🔄 Sync Contacts", callback_data="action_sync_contacts"),
         InlineKeyboardButton("🔄 Sync Membres", callback_data="action_sync_members")],
        [InlineKeyboardButton("🔄 Sync Adhésions", callback_data="action_sync_memberships"),
         InlineKeyboardButton("🔄 Sync Cotisations", callback_data="action_sync_contributions")],
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "action_sync_contacts":
        await query.edit_message_text(text="Utilisez la commande /sync pour synchroniser les contacts.")
    elif query.data == "action_sync_members":
        await query.edit_message_text(text="Utilisez la commande /sync_members pour synchroniser les adhérents.")
    elif query.data == "action_sync_memberships":
        await query.edit_message_text(text="Utilisez la commande /sync_memberships pour synchroniser les adhésions.")
    elif query.data == "action_sync_contributions":
        await query.edit_message_text(text="Utilisez la commande /sync_contributions pour synchroniser les cotisations.")
