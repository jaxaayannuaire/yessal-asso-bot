from telegram import Update
from telegram.ext import ContextTypes

from core.auth import AuthManager, BOARD_ROLES
from core.db import DatabaseManager
from services.dolibarr_api import DolibarrClient


async def sync_members_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auth = AuthManager()
    user = auth.get_user(str(update.effective_user.id))
    if not user or user[2] not in BOARD_ROLES:
        await update.message.reply_text("⛔ Accès refusé.")
        return

    await update.message.reply_text("⏳ Téléchargement des adhérents...")
    success, data = DolibarrClient().get_members()
    if not success:
        await update.message.reply_text(f"❌ Erreur : {data}")
        return

    db = DatabaseManager()
    try:
        _, msg = db.sync_members(data)
    finally:
        db.close()
    await update.message.reply_text(msg)


async def search_member_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auth = AuthManager()
    user = auth.get_user(str(update.effective_user.id))
    if not user or not user[4] or user[2] not in BOARD_ROLES:
        await update.message.reply_text("⛔ Accès refusé.")
        return
    if not context.args:
        await update.message.reply_text("⚠️ Exemple : /membre fall")
        return

    db = DatabaseManager()
    try:
        results = db.search_members(" ".join(context.args))
    finally:
        db.close()

    if not results:
        await update.message.reply_text("🔍 Aucun adhérent trouvé.")
        return

    lines = ["👥 Adhérents trouvés :", ""]
    for result in results:
        statut = "🟢 Actif" if result[4] == "1" else "🔴 Inactif"
        lines.extend([
            f"👤 {result[1]} {result[2]}",
            f"📱 {result[3] or 'N/A'}",
            f"Statut : {statut}",
            f"Exp : {result[5] or 'N/A'}",
            "---",
        ])
    await update.message.reply_text("\n".join(lines))
