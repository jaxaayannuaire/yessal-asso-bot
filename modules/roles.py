"""Administration et attribution des groupes métier Yessal dans Dolibarr.

Phase 17A.4:
- les rôles métier sont attribués à partir d'un ID utilisateur Dolibarr;
- Dolibarr reste la source de vérité des rôles;
- DuckDB ne conserve qu'un miroir technique;
- seuls les Super Admins peuvent nommer un rôle;
- après attribution, le menu Telegram du compte lié est rafraîchi.
"""

import logging
import os

from telegram import BotCommand, BotCommandScopeChat, Update
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

ROLE_COMMANDS = {
    ROLE_PRESIDENT: "nommer_president",
    ROLE_BUREAU: "nommer_bureau",
    ROLE_TRESORIER: "nommer_tresorier",
    ROLE_ADMIN: "nommer_admin",
    ROLE_MEMBRE: "nommer_membre",
}


def _authorized(update: Update) -> bool:
    return AuthManager().is_super_admin(str(update.effective_user.id))


def _numeric_id(context: ContextTypes.DEFAULT_TYPE):
    return (
        context.args[0].strip()
        if len(context.args) == 1 and context.args[0].isdigit()
        else None
    )


def _bootstrap_allowed(telegram_id: str) -> bool:
    """Autorise le bootstrap uniquement aux Telegram IDs explicitement configurés."""
    configured = os.getenv("TELEGRAM_ADMIN_IDS", "")
    allowed = {
        item.strip()
        for item in configured.replace(";", ",").split(",")
        if item.strip()
    }
    return str(telegram_id) in allowed


async def bootstrap_super_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bootstrap initial : lie un Telegram autorisé à un utilisateur Dolibarr."""
    telegram_id = str(update.effective_user.id)

    if not _bootstrap_allowed(telegram_id):
        await update.message.reply_text(
            "⛔ Bootstrap refusé : votre Telegram ID n'est pas autorisé "
            "dans TELEGRAM_ADMIN_IDS."
        )
        return

    did = _numeric_id(context)
    if not did:
        await update.message.reply_text(
            "Usage : /bootstrap_super_admin <ID_DOLIBARR>\n"
            "Exemple : /bootstrap_super_admin 7"
        )
        return

    db = DatabaseManager()
    client = DolibarrClient()

    try:
        ensure_schema(db)
        conn = db.connect()

        existing = conn.execute(
            "SELECT COUNT(*) FROM bot_users "
            "WHERE is_active = true AND role = ?",
            [ROLE_SUPER_ADMIN],
        ).fetchone()[0]

        if existing:
            await update.message.reply_text(
                "⛔ Bootstrap déjà effectué. Un Super Admin existe déjà."
            )
            return

        user = find_dolibarr_user(db, did)
        if not user:
            ok, message = sync_from_dolibarr(client, db)
            if not ok:
                await update.message.reply_text(message)
                return
            user = find_dolibarr_user(db, did)

        if not user:
            await update.message.reply_text(
                f"❌ ID Dolibarr {did} introuvable après synchronisation."
            )
            return

        group = find_group_by_role(db, ROLE_SUPER_ADMIN)
        if group:
            group_id = group[0]
        else:
            ok, result = client.create_dolibarr_group(
                ROLE_GROUP_NAMES[ROLE_SUPER_ADMIN]
            )
            if not ok:
                await update.message.reply_text(
                    f"❌ Impossible de créer {ROLE_GROUP_NAMES[ROLE_SUPER_ADMIN]} : {result}"
                )
                return

            ok, message = sync_from_dolibarr(client, db)
            if not ok:
                await update.message.reply_text(message)
                return

            group = find_group_by_role(db, ROLE_SUPER_ADMIN)
            if not group:
                await update.message.reply_text(
                    "❌ Groupe Super Admin créé mais introuvable après synchronisation."
                )
                return
            group_id = group[0]

        ok, result = client.add_user_to_group(user[0], group_id)
        if not ok:
            await update.message.reply_text(
                f"❌ Impossible d'ajouter l'ID Dolibarr {did} au groupe "
                f"{ROLE_GROUP_NAMES[ROLE_SUPER_ADMIN]} : {result}"
            )
            return

        conn.execute(
            """
            INSERT OR REPLACE INTO bot_users
            (telegram_id, username, role, dolibarr_contact_id, is_active, dolibarr_user_id)
            VALUES (?, ?, ?, NULL, true, ?)
            """,
            [
                telegram_id,
                update.effective_user.username or "",
                ROLE_SUPER_ADMIN,
                did,
            ],
        )

        ok, message = sync_from_dolibarr(client, db)
        if not ok:
            await update.message.reply_text(
                "⚠️ Bootstrap effectué, mais la resynchronisation du miroir a échoué : "
                + message
            )
            return

        await update.message.reply_text(
            "✅ Bootstrap Super Admin terminé.\n\n"
            f"Telegram ID : {telegram_id}\n"
            f"Dolibarr ID : {did}\n"
            f"Groupe : {ROLE_GROUP_NAMES[ROLE_SUPER_ADMIN]}\n\n"
            "Vous pouvez maintenant utiliser /creer_groupes pour créer les autres "
            "groupes métier Yessal."
        )
    finally:
        db.close()


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
    if not _authorized(update):
        await update.message.reply_text("⛔ Réservé au Super Admin.")
        return

    db = DatabaseManager()
    client = DolibarrClient()
    try:
        sync_ok, msg = sync_from_dolibarr(client, db)
        if not sync_ok:
            await update.message.reply_text(msg)
            return

        created, existing = [], []

        for role in MANAGED_ROLES:
            if find_group_by_role(db, role):
                existing.append(ROLE_GROUP_NAMES[role])
                continue

            ok, result = client.create_dolibarr_group(ROLE_GROUP_NAMES[role])
            if not ok:
                await update.message.reply_text(
                    f"⚠️ Création de {ROLE_GROUP_NAMES[role]} impossible : {result}"
                )
                return

            created.append(ROLE_GROUP_NAMES[role])

        ok, message = sync_from_dolibarr(client, db)
        if not ok:
            await update.message.reply_text(message)
            return

        lines = ["👥 GROUPES MÉTIER YESSAL", ""]
        if created:
            lines.append("✅ Créés : " + ", ".join(created))
        if existing:
            lines.append("ℹ️ Déjà présents : " + ", ".join(existing))
        lines.append(
            "🔒 Les groupes techniques, dont « Yessal Asso Bot », n'ont pas été modifiés."
        )

        await update.message.reply_text("\n".join(lines))
    finally:
        db.close()


async def link_me_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        await update.message.reply_text("⛔ Réservé au Super Admin.")
        return

    did = _numeric_id(context)
    if not did:
        await update.message.reply_text(
            "Usage : /lier_moi <ID_DOLIBARR>\nExemple : /lier_moi 7"
        )
        return

    db = DatabaseManager()
    try:
        ensure_schema(db)
        user = find_dolibarr_user(db, did)

        if not user:
            await update.message.reply_text(
                f"❌ ID Dolibarr {did} introuvable. Faites /sync_roles."
            )
            return

        db.connect().execute(
            """
            INSERT OR REPLACE INTO bot_users
            (telegram_id, username, role, dolibarr_contact_id, is_active, dolibarr_user_id)
            VALUES (
                ?, ?,
                COALESCE(
                    (SELECT role FROM bot_users WHERE telegram_id = ?),
                    'user'
                ),
                NULL, true, ?
            )
            """,
            [
                str(update.effective_user.id),
                update.effective_user.username or "",
                str(update.effective_user.id),
                str(user[0]),
            ],
        )

        await update.message.reply_text(
            f"✅ Compte Telegram lié à l'utilisateur Dolibarr ID {user[0]}.\n"
            f"Utilisateur : {user[2]} {user[3]} ({user[1]})\n\n"
            "Les rôles Telegram proviennent uniquement des groupes métier YESSAL_* de Dolibarr."
        )
    finally:
        db.close()


def _role_assignment_usage(role: str) -> str:
    command = ROLE_COMMANDS[role]
    return f"Usage : /{command} <ID_DOLIBARR>\nExemple : /{command} 7"


def _linked_telegram_ids(db, dolibarr_user_id: str) -> list[str]:
    """Retourne les comptes Telegram liés au même utilisateur Dolibarr."""
    rows = db.connect().execute(
        """
        SELECT telegram_id
        FROM bot_users
        WHERE dolibarr_user_id = ?
          AND is_active = true
        """,
        [str(dolibarr_user_id)],
    ).fetchall()
    return [str(row[0]) for row in rows]


async def _refresh_linked_menus(bot, db, dolibarr_user_id: str) -> None:
    """Rafraîchit les menus Telegram après une modification de rôle."""
    for telegram_id in _linked_telegram_ids(db, dolibarr_user_id):
        try:
            await refresh_command_menu(bot, telegram_id)
        except Exception:
            logger.exception(
                "Échec du rafraîchissement du menu Telegram pour %s",
                telegram_id,
            )


async def _assign_role(update: Update, context: ContextTypes.DEFAULT_TYPE, role: str):
    """Ajoute un utilisateur Dolibarr au groupe métier correspondant."""
    if not _authorized(update):
        await update.message.reply_text("⛔ Réservé au Super Admin.")
        return

    did = _numeric_id(context)
    if not did:
        await update.message.reply_text(_role_assignment_usage(role))
        return

    db = DatabaseManager()
    client = DolibarrClient()

    try:
        ensure_schema(db)

        # Toujours synchroniser avant la décision : Dolibarr est la source de vérité.
        sync_ok, sync_message = sync_from_dolibarr(client, db)
        if not sync_ok:
            await update.message.reply_text(sync_message)
            return

        target = find_dolibarr_user(db, did)
        if not target:
            await update.message.reply_text(
                f"❌ Utilisateur Dolibarr ID {did} introuvable."
            )
            return

        if not target[5]:
            await update.message.reply_text(
                f"❌ L'utilisateur Dolibarr ID {did} est désactivé."
            )
            return

        group = find_group_by_role(db, role)
        if not group:
            await update.message.reply_text(
                f"❌ Groupe {ROLE_GROUP_NAMES[role]} introuvable. "
                "Utilisez /creer_groupes."
            )
            return

        ok, result = client.add_user_to_group(target[0], group[0])
        if not ok:
            await update.message.reply_text(
                f"❌ Impossible d'ajouter l'ID Dolibarr {did} à "
                f"{ROLE_GROUP_NAMES[role]} : {result}"
            )
            return

        # Le groupe Dolibarr vient d'être modifié : on resynchronise immédiatement.
        sync_ok, sync_message = sync_from_dolibarr(client, db)
        if not sync_ok:
            await update.message.reply_text(
                "⚠️ Rôle attribué dans Dolibarr, mais la synchronisation du miroir "
                f"a échoué : {sync_message}"
            )
            return

        await _refresh_linked_menus(
            update.get_bot(),
            db,
            str(target[0]),
        )

        await update.message.reply_text(
            f"✅ Rôle attribué.\n\n"
            f"Utilisateur Dolibarr : {target[0]}\n"
            f"Nom : {target[2]} {target[3]}\n"
            f"Groupe : {ROLE_GROUP_NAMES[role]}\n\n"
            "Les permissions Telegram sont désormais calculées depuis les groupes "
            "métier Dolibarr."
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

    await update.message.reply_text(
        "🔐 Vos rôles\n\n"
        + (
            "\n".join(f"• {role}" for role in roles)
            if roles
            else "⛔ Aucun rôle métier actif."
        )
    )


async def refresh_command_menu(bot, telegram_id):
    """Met à jour le menu Telegram selon les permissions actuelles."""
    auth = AuthManager()
    telegram_id = str(telegram_id)
    roles = auth.get_roles(telegram_id)

    commands = [
        BotCommand("start", "Accueil"),
        BotCommand("roles", "Voir mes rôles"),
        BotCommand("dashboard", "Tableau de bord"),
    ]

    if "membre" in roles or "user" in roles:
        commands.append(BotCommand("membre", "Ma situation adhérent"))

    if (
        auth.has_permission(telegram_id, "members.view")
        or auth.has_permission(telegram_id, "reports.view")
    ):
        commands.extend(
            [
                BotCommand("report", "Rapport"),
                BotCommand("sync_members", "Synchroniser les adhérents"),
            ]
        )

    if auth.has_permission(telegram_id, "caisse.view"):
        commands.append(BotCommand("caisse", "Situation caisse"))

    if auth.has_permission(telegram_id, "caisse.create"):
        commands.extend(
            [
                BotCommand("entree", "Préparer une entrée"),
                BotCommand("sortie", "Préparer une sortie"),
            ]
        )

    if auth.has_permission(telegram_id, "roles.manage"):
        commands.extend(
            [
                BotCommand("sync_roles", "Synchroniser les rôles"),
                BotCommand("creer_groupes", "Créer les groupes Yessal"),
                BotCommand("lier_moi", "Lier un utilisateur Dolibarr par ID"),
                BotCommand("nommer_tresorier", "Nommer un trésorier par ID"),
                BotCommand("nommer_president", "Nommer le président par ID"),
                BotCommand("nommer_bureau", "Nommer le bureau par ID"),
                BotCommand("nommer_admin", "Nommer un administrateur par ID"),
                BotCommand("nommer_membre", "Nommer un membre par ID"),
            ]
        )

    try:
        await bot.set_my_commands(
            commands,
            scope=BotCommandScopeChat(chat_id=int(telegram_id)),
        )
    except Exception:
        logger.exception(
            "Impossible de mettre à jour le menu Telegram pour %s",
            telegram_id,
        )
