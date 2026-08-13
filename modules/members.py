from telegram import Update
from telegram.ext import ContextTypes
import logging
from services.dolibarr_api import DolibarrClient
from core.db import DatabaseManager
from core.auth import AuthManager

logger = logging.getLogger(__name__)

async def sync_members_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auth = AuthManager()
    user = auth.get_user(str(update.effective_user.id))
    if not user or user[2] not in ['super_admin', 'president', 'tresorier']:
        await update.message.reply_text("⛔ Vous n'avez pas l'autorisation.")
        return
    await update.message.reply_text("⏳ Téléchargement des adhérents depuis Dolibarr...")
    client = DolibarrClient()
    success, data = client.get_members()
    if success:
        db = DatabaseManager()
        sync_success, message = db.sync_members(data)
        db.close()
        await update.message.reply_text(message)
    else:
        await update.message.reply_text(f"❌ Erreur lors de la lecture des adhérents : {data}")

async def search_member_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auth = AuthManager()
    user = auth.get_user(str(update.effective_user.id))
    if not user or user[2] == 'user':
        await update.message.reply_text("⛔ Accès refusé.")
        return
    if not context.args:
        await update.message.reply_text("⚠️ Veuillez préciser un nom ou prénom.\nExemple : /membre fall")
        return
    query = " ".join(context.args)
    db = DatabaseManager()
    results = db.search_members(query)
    db.close()
    if not results:
        await update.message.reply_text(f"🔍 Aucun adhérent trouvé pour '{query}'.")
        return
    message = f"👥 Adhérents trouvés pour '{query}' :\n\n"
    for r in results:
        statut_txt = "🟢 Actif" if r[4] == '1' else "🔴 Inactif/Expiré"
        message += f"👤 {r[0]} - {r[1]} {r[2]}\n📱 {r[3] or 'Non renseigné'}\nStatut : {statut_txt}\nExp : {r[5] or 'N/A'}\n〰️〰️〰️\n"
    await update.message.reply_text(message)
