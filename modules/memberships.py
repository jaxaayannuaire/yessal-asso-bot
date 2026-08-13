from telegram import Update
from telegram.ext import ContextTypes
from services.dolibarr_api import DolibarrClient
from core.db import DatabaseManager
from core.auth import AuthManager

async def sync_memberships_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auth = AuthManager()
    user = auth.get_user(str(update.effective_user.id))
    if not user or user[2] not in ['super_admin', 'president', 'tresorier']:
        await update.message.reply_text("⛔ Accès refusé.")
        return
    await update.message.reply_text("⏳ Téléchargement des adhésions...")
    client = DolibarrClient()
    success, data = client.get_memberships()
    if success:
        db = DatabaseManager()
        _, msg = db.sync_memberships(data)
        db.close()
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text(f"❌ Erreur : {data}")
