from telegram import Update
from telegram.ext import ContextTypes

from core.auth import AuthManager, BOARD_ROLES
from core.db import DatabaseManager
from services.dolibarr_api import DolibarrClient


async def sync_contacts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auth = AuthManager()
    user = auth.get_user(str(update.effective_user.id))
    if not user or user[2] not in BOARD_ROLES:
        await update.message.reply_text("⛔ Accès refusé.")
        return

    await update.message.reply_text("⏳ Téléchargement des contacts...")
    success, data = DolibarrClient().get_contacts()
    if not success:
        await update.message.reply_text(f"❌ Erreur : {data}")
        return

    db = DatabaseManager()
    try:
        _, msg = db.sync_contacts(data)
    finally:
        db.close()
    await update.message.reply_text(msg)


async def search_contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auth = AuthManager()
    user = auth.get_user(str(update.effective_user.id))
    if not user or not user[4] or user[2] not in BOARD_ROLES:
        await update.message.reply_text("⛔ Accès refusé.")
        return
    if not context.args:
        await update.message.reply_text("⚠️ Exemple : /contact diallo")
        return

    db = DatabaseManager()
    try:
        results = db.search_contacts(" ".join(context.args))
    finally:
        db.close()

    if not results:
        await update.message.reply_text("🔍 Aucun contact trouvé.")
        return

    lines = ["🔍 Résultats :", ""]
    for result in results:
        lines.extend([
            f"👤 {result[1]} {result[2]}",
            f"📱 {result[3] or 'N/A'}",
            f"ID: {result[0]}",
            "---",
        ])
    await update.message.reply_text("\n".join(lines))
