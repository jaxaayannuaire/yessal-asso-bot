from telegram import Update
from telegram.ext import ContextTypes
import logging

from services.dolibarr_api import DolibarrClient
from core.db import DatabaseManager
from core.auth import AuthManager

logger = logging.getLogger(__name__)

async def sync_memberships_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /sync_memberships : Force la mise à jour des adhésions"""
    user_id = str(update.effective_user.id)
    
    auth = AuthManager()
    user = auth.get_user(user_id)
    if not user or user[2] not in ['super_admin', 'president', 'tresorier']:
        await update.message.reply_text("⛔ Vous n'avez pas l'autorisation.")
        return

    await update.message.reply_text("⏳ Téléchargement des adhésions depuis Dolibarr...")
    
    client = DolibarrClient()
    success, data = client.get_memberships()
    
    if success:
        db = DatabaseManager()
        sync_success, message = db.sync_memberships(data)
        db.close()
        await update.message.reply_text(message)
    else:
        await update.message.reply_text(f"❌ Erreur lors de la lecture des adhésions : {data}")
