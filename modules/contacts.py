from telegram import Update
from telegram.ext import ContextTypes
from services.dolibarr_api import DolibarrClient
from core.db import DatabaseManager
from core.auth import AuthManager

async def sync_contacts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auth = AuthManager()
    user = auth.get_user(str(update.effective_user.id))
    if not user or user[2] not in ['super_admin', 'president', 'tresorier']:
        await update.message.reply_text("⛔ Accès refusé.")
        return
    await update.message.reply_text("⏳ Téléchargement des contacts...")
    client = DolibarrClient()
    success, data = client.get_contacts()
    if success:
        db = DatabaseManager()
        _, msg = db.sync_contacts(data)
        db.close()
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text(f"❌ Erreur : {data}")

async def search_contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auth = AuthManager()
    user = auth.get_user(str(update.effective_user.id))
    if not user or user[2] == 'user':
        await update.message.reply_text("⛔ Accès refusé.")
        return
    if not context.args:
        await update.message.reply_text("⚠️ Exemple : /contact diallo")
        return
    db = DatabaseManager()
    results = db.search_contacts(" ".join(context.args))
    db.close()
    if not results:
        await update.message.reply_text("🔍 Aucun contact trouvé.")
        return
    msg = "🔍 Résultats :

"
    for r in results:
        msg += f"👤 {r[1]} {r[2]}
📱 {r[3] or 'N/A'}
ID: {r[0]}
---
"
    await update.message.reply_text(msg)
