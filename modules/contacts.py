from telegram import Update
from telegram.ext import ContextTypes
import logging
from services.dolibarr_api import DolibarrClient
from core.db import DatabaseManager
from core.auth import AuthManager

logger = logging.getLogger(__name__)

async def sync_contacts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auth = AuthManager()
    user = auth.get_user(str(update.effective_user.id))
    if not user or user[2] not in ['super_admin', 'president', 'tresorier']:
        await update.message.reply_text("⛔ Vous n'avez pas l'autorisation.")
        return
    await update.message.reply_text("⏳ Téléchargement des contacts depuis Dolibarr...")
    client = DolibarrClient()
    success, data = client.get_contacts()
    if success:
        db = DatabaseManager()
        sync_success, message = db.sync_contacts(data)
        db.close()
        await update.message.reply_text(message)
    else:
        await update.message.reply_text(f"❌ Erreur lors de la lecture Dolibarr : {data}")

async def search_contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auth = AuthManager()
    user = auth.get_user(str(update.effective_user.id))
    if not user or user[2] == 'user':
        await update.message.reply_text("⛔ Accès refusé.")
        return
    if not context.args:
        await update.message.reply_text("⚠️ Veuillez préciser un nom, prénom ou numéro.\nExemple : /contact diallo")
        return
    query = " ".join(context.args)
    db = DatabaseManager()
    results = db.search_contacts(query)
    db.close()
    if not results:
        await update.message.reply_text(f"🔍 Aucun contact trouvé pour '{query}'.")
        return
    message = f"🔍 Résultats pour '{query}' :\n\n"
    for r in results:
        message += f"👤 {r[1]} {r[2]}\n📱 {r[3] or 'Non renseigné'}\nID Dolibarr: {r[0]}\n〰️〰️〰️\n"
    await update.message.reply_text(message)
