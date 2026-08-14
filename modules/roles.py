"""Gestion des utilisateurs, groupes et permissions Dolibarr pour Telegram."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from core.auth import AuthManager
from core.db import DatabaseManager
from core.permissions import (
    ROLE_ADMIN,
    ROLE_BUREAU,
    ROLE_MEMBRE,
    ROLE_PRESIDENT,
    ROLE_SUPER_ADMIN,
    ROLE_TRESORIER,
    ROLE_GROUP_NAMES,
    ensure_schema,
    find_dolibarr_user,
    find_group_by_role,
    sync_from_dolibarr,
)
from services.dolibarr_api import DolibarrClient

logger = logging.getLogger(__name__)

MANAGED_ROLES = (
    ROLE_SUPER_ADMIN,
    ROLE_PRESIDENT,
    ROLE_BUREAU,
    ROLE_TRESORIER,
    ROLE_ADMIN,
    ROLE_MEMBRE,
)


def _authorized(update: Update) -> bool:
    return AuthManager().is_super_admin(str(update.effective_user.id))


async def sync_roles_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        await update.message.reply_text("⛔ Réservé au Super Admin.")
        return
    db = DatabaseManager()
    try:
        ok, message = sync_from_dolibarr(DolibarrClient(), db)
    finally:
        db.close()
    await update.message.reply_text(message)


async def create_roles_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Crée les groupes Yessal standard s'ils n'existent pas encore."""
    if not _authorized(update):
        await update.message.reply_text("⛔ Réservé au Super Admin.")
        return

    db = DatabaseManager()
    client = DolibarrClient()
    try:
        sync_ok, sync_message = sync_from_dolibarr(client, db)
        if not sync_ok:
            await update.message.reply_text(sync_message)
            return

        created = []
        existing = []
        for role in MANAGED_ROLES:
            if find_group_by_role(db, role):
                existing.append(ROLE_GROUP_NAMES[role])
                continue
            ok, result = client.create_dolibarr_group(ROLE_GROUP_NAMES[role])
            if ok:
                created.append(ROLE_GROUP_NAMES[role])
            else:
                logger.warning("Création groupe %s échouée: %s", role, result)
                await update.message.reply_text(
                    f"⚠️ Impossible de créer le groupe {ROLE_GROUP_NAMES[role]} : {result}\n\n"
                    "Vérifiez les droits de la clé API Dolibarr."
                )
                return

        sync_from_dolibarr(client, db)
        lines = ["👥 *GROUPES YESSAL*", ""]
        if created:
            lines.append("✅ Créés : " + ", ".join(created))
        if existing:
            lines.append("ℹ️ Déjà présents : " + ", ".join(existing))
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    finally:
        db.close()


async def link_me_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        await update.message.reply_text("⛔ Réservé au Super Admin.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage : /lier_moi <login_ou_id_dolibarr>")
        return

    db = DatabaseManager()
    try:
        ensure_schema(db)
        user = find_dolibarr_user(db, context.args[0])
        if not user:
            await update.message.reply_text("❌ Utilisateur Dolibarr introuvable. Faites d'abord /sync_roles.")
            return
        db.connect().execute(
            """
            INSERT OR REPLACE INTO bot_users
            (telegram_id, username, role, dolibarr_contact_id, is_active, dolibarr_user_id)
            VALUES (?, ?, COALESCE((SELECT role FROM bot_users WHERE telegram_id = ?), 'user'),
                    NULL, true, ?)
            """,
            [str(update.effective_user.id), update.effective_user.username or "", str(update.effective_user.id), str(user[0])],
        )
        await update.message.reply_text(
            f"✅ Telegram lié à Dolibarr : *{user[1]}* (ID {user[0]}).\n"
            "Les permissions seront désormais calculées depuis les groupes Dolibarr après synchronisation.",
            parse_mode="Markdown",
        )
    finally:
        db.close()


async def _assign_role(update: Update, context: ContextTypes.DEFAULT_TYPE, role: str):
    if not _authorized(update):
        await update.message.reply_text("⛔ Réservé au Super Admin.")
        return
    if len(context.args) != 1:
        await update.message.reply_text(f"Usage : /nommer_{role} <login_ou_id_dolibarr>")
        return

    db = DatabaseManager()
    client = DolibarrClient()
    try:
        ensure_schema(db)
        target = find_dolibarr_user(db, context.args[0])
        group = find_group_by_role(db, role)
        if not target:
            await update.message.reply_text("❌ Utilisateur Dolibarr introuvable. Faites /sync_roles.")
            return
        if not group:
            await update.message.reply_text(
                f"❌ Groupe Dolibarr *{ROLE_GROUP_NAMES[role]}* introuvable.\n"
                "Créez les groupes dans Dolibarr ou utilisez /creer_groupes.",
                parse_mode="Markdown",
            )
            return

        ok, result = client.add_user_to_group(target[0], group[0])
        if not ok:
            await update.message.reply_text(f"❌ Impossible de nommer l'utilisateur : {result}")
            return

        sync_from_dolibarr(client, db)
        await update.message.reply_text(
            f"✅ *{target[1]}* est maintenant dans le groupe *{group[1]}*.\n"
            "Les permissions Telegram ont été synchronisées.",
            parse_mode="Markdown",
        )
    finally:
        db.close()


async def nommer_tresorier_command(update, context):
    await _assign_role(update, context, ROLE_TRESORIER)


async def nommer_president_command(update, context):
    await _assign_role(update, context, ROLE_PRESIDENT)


async def nommer_bureau_command(update, context):
    await _assign_role(update, context, ROLE_BUREAU)


async def nommer_admin_command(update, context):
    await _assign_role(update, context, ROLE_ADMIN)


async def nommer_membre_command(update, context):
    await _assign_role(update, context, ROLE_MEMBRE)


async def roles_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auth = AuthManager()
    roles = sorted(auth.get_roles(str(update.effective_user.id)))
    if not roles:
        await update.message.reply_text("⛔ Aucun rôle actif.")
        return
    await update.message.reply_text("🔐 *Vos rôles*\n\n" + "\n".join(f"• `{role}`" for role in roles), parse_mode="Markdown")

async def refresh_command_menu(bot, telegram_id):
    """Expose uniquement les commandes pertinentes dans le menu Telegram du chat."""
    from telegram import BotCommand, BotCommandScopeChat

    auth = AuthManager()
    permissions = auth.get_roles(str(telegram_id))
    commands = [
        BotCommand("start", "Accueil"),
        BotCommand("roles", "Voir mes rôles"),
        BotCommand("dashboard", "Tableau de bord"),
    ]
    if "membre" in permissions or "user" in permissions:
        commands += [BotCommand("membre", "Ma situation adhérent")]
    if any(auth.has_permission(telegram_id, p) for p in ("members.view", "reports.view")):
        commands += [BotCommand("report", "Rapport"), BotCommand("sync_members", "Synchroniser les adhérents")]
    if auth.has_permission(telegram_id, "caisse.view"):
        commands += [BotCommand("caisse", "Situation caisse")]
    if auth.has_permission(telegram_id, "caisse.create"):
        commands += [BotCommand("entree", "Préparer une entrée"), BotCommand("sortie", "Préparer une sortie")]
    if auth.has_permission(telegram_id, "roles.manage") or auth.is_super_admin(telegram_id):
        commands += [
            BotCommand("sync_roles", "Synchroniser les rôles"),
            BotCommand("creer_groupes", "Créer les groupes Yessal"),
            BotCommand("lier_moi", "Lier un utilisateur Dolibarr"),
            BotCommand("nommer_tresorier", "Nommer un trésorier"),
            BotCommand("nommer_president", "Nommer le président"),
            BotCommand("nommer_bureau", "Nommer le bureau"),
            BotCommand("nommer_admin", "Nommer un administrateur"),
        ]
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=telegram_id))
    except Exception:
        logger.exception("Impossible de mettre à jour le menu Telegram pour %s", telegram_id)
