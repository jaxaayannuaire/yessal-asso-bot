from telegram import Update
from telegram.ext import ContextTypes

from core.auth import AuthManager, BOARD_ROLES, ROLE_SUPER_ADMIN, ROLE_TRESORIER
from core.db import DatabaseManager
from services.dolibarr_api import DolibarrClient


async def sync_memberships_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /sync_memberships : synchronise les adhésions."""
    user = AuthManager().get_user(str(update.effective_user.id))
    if not user or user[2] not in BOARD_ROLES:
        await update.message.reply_text("⛔ Accès réservé au Bureau/Trésorier.")
        return

    await update.message.reply_text("⏳ Téléchargement des adhésions...")
    success, data = DolibarrClient().get_memberships()
    if not success:
        await update.message.reply_text(f"❌ Erreur Dolibarr : {data}")
        return

    db = DatabaseManager()
    try:
        _, msg = db.sync_memberships(data)
    finally:
        db.close()
    await update.message.reply_text(msg)


async def sync_contributions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /sync_contributions : synchronise les cotisations."""
    user = AuthManager().get_user(str(update.effective_user.id))
    if not user or user[2] not in {ROLE_SUPER_ADMIN, ROLE_TRESORIER}:
        await update.message.reply_text("⛔ Accès réservé au Trésorier.")
        return

    await update.message.reply_text("⏳ Téléchargement des cotisations...")
    success, data = DolibarrClient().get_contributions()
    if not success:
        await update.message.reply_text(f"❌ Erreur Dolibarr : {data}")
        return

    db = DatabaseManager()
    try:
        _, msg = db.sync_contributions(data)
    finally:
        db.close()
    await update.message.reply_text(msg)
