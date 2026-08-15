"""Secure Telegram <-> Dolibarr pairing for Phase 17A.5."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from core.auth import AuthManager
from core.db import DatabaseManager
from core.permissions import ensure_schema, sync_from_dolibarr
from services.dolibarr_api import DolibarrClient

PAIRING_TTL_MINUTES = 10
TOKEN_BYTES = 32


def _hash_token(token: str) -> str:
    return hashlib.sha256((token or "").strip().encode("utf-8")).hexdigest()


def _ensure_token_table(db):
    ensure_schema(db)
    db.connect().execute("""
        CREATE TABLE IF NOT EXISTS telegram_link_tokens (
            token_hash VARCHAR PRIMARY KEY,
            dolibarr_user_id VARCHAR NOT NULL,
            created_by_telegram_id VARCHAR NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _now_naive_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_dolibarr_user_active(user):
    value = user.get("statut", user.get("status", user.get("active", 0)))
    try:
        return int(value) == 1
    except (TypeError, ValueError):
        return bool(value)


def create_pairing_token(db, dolibarr_user_id, created_by_telegram_id,
                         ttl_minutes=PAIRING_TTL_MINUTES):
    user_id = str(dolibarr_user_id).strip()
    creator_id = str(created_by_telegram_id).strip()
    if not user_id.isdigit():
        raise ValueError("L'ID Dolibarr doit être numérique.")
    if not creator_id:
        raise ValueError("Telegram ID du créateur manquant.")

    _ensure_token_table(db)
    raw = secrets.token_urlsafe(TOKEN_BYTES)
    token_hash = _hash_token(raw)
    expires_at = _now_naive_utc() + timedelta(minutes=int(ttl_minutes))
    conn = db.connect()

    conn.execute("""
        UPDATE telegram_link_tokens
        SET used_at=CURRENT_TIMESTAMP
        WHERE dolibarr_user_id=? AND used_at IS NULL
          AND expires_at>CURRENT_TIMESTAMP
    """, [user_id])
    conn.execute("""
        INSERT INTO telegram_link_tokens
        (token_hash,dolibarr_user_id,created_by_telegram_id,expires_at)
        VALUES (?,?,?,?)
    """, [token_hash, user_id, creator_id, expires_at])
    return raw, expires_at


def consume_pairing_token(db, raw_token, telegram_id, username=""):
    token = (raw_token or "").strip()
    if not token:
        return False, "Jeton manquant."

    _ensure_token_table(db)
    conn = db.connect()
    row = conn.execute("""
        SELECT token_hash,dolibarr_user_id,expires_at,used_at
        FROM telegram_link_tokens WHERE token_hash=? LIMIT 1
    """, [_hash_token(token)]).fetchone()

    if not row:
        return False, "Jeton invalide."
    _, dolibarr_user_id, expires_at, used_at = row
    if used_at is not None:
        return False, "Ce jeton a déjà été utilisé."
    if expires_at <= _now_naive_utc():
        return False, "Ce jeton a expiré."

    client = DolibarrClient()
    ok_user, user = client.get_dolibarr_user(dolibarr_user_id)
    if not ok_user or not isinstance(user, dict):
        return False, f"Impossible de vérifier l'utilisateur Dolibarr : {user}"
    if not _is_dolibarr_user_active(user):
        return False, "L'utilisateur Dolibarr est désactivé."

    telegram_id = str(telegram_id).strip()
    if not telegram_id:
        return False, "Telegram ID manquant."

    existing = conn.execute("""
        SELECT dolibarr_user_id FROM bot_users
        WHERE telegram_id=? AND is_active=TRUE LIMIT 1
    """, [telegram_id]).fetchone()
    if existing and str(existing[0]) != str(dolibarr_user_id):
        return False, "Ce compte Telegram est déjà lié à un autre utilisateur Dolibarr."

    existing = conn.execute("""
        SELECT telegram_id FROM bot_users
        WHERE dolibarr_user_id=? AND is_active=TRUE LIMIT 1
    """, [str(dolibarr_user_id)]).fetchone()
    if existing and str(existing[0]) != telegram_id:
        return False, "Cet utilisateur Dolibarr possède déjà un compte Telegram lié."

    conn.execute("""
        INSERT OR REPLACE INTO bot_users
        (telegram_id,username,role,dolibarr_contact_id,is_active,created_at,dolibarr_user_id)
        VALUES (?,?,'user',NULL,TRUE,
                COALESCE((SELECT created_at FROM bot_users WHERE telegram_id=?),
                         CURRENT_TIMESTAMP),?)
    """, [telegram_id, username or "", telegram_id, str(dolibarr_user_id)])
    conn.execute("""
        UPDATE telegram_link_tokens SET used_at=CURRENT_TIMESTAMP
        WHERE token_hash=? AND used_at IS NULL
    """, [_hash_token(token)])

    db.add_audit_event(
        "telegram_account_linked",
        actor_telegram_id=telegram_id,
        entity_type="dolibarr_user",
        entity_id=str(dolibarr_user_id),
        details=f"Dolibarr login={user.get('login', '')}",
    )
    return True, {
        "dolibarr_user_id": str(dolibarr_user_id),
        "firstname": user.get("firstname") or "",
        "lastname": user.get("lastname") or "",
        "login": user.get("login") or "",
    }


async def generate_link_command(update, context):
    telegram_id = str(update.effective_user.id)
    if not AuthManager().is_super_admin(telegram_id):
        await update.message.reply_text("⛔ Accès réservé au Super Admin.")
        return

    if len(context.args) != 1 or not str(context.args[0]).strip().isdigit():
        await update.message.reply_text(
            "Usage : /generer_lien <ID_DOLIBARR>\nExemple : /generer_lien 6"
        )
        return

    dolibarr_user_id = str(context.args[0]).strip()
    client = DolibarrClient()
    ok, user = client.get_dolibarr_user(dolibarr_user_id)
    if not ok or not isinstance(user, dict):
        await update.message.reply_text(
            f"❌ Impossible de vérifier l'utilisateur Dolibarr {dolibarr_user_id} :\n{user}"
        )
        return
    if not _is_dolibarr_user_active(user):
        await update.message.reply_text(
            f"❌ L'utilisateur Dolibarr {dolibarr_user_id} est désactivé."
        )
        return

    db = DatabaseManager()
    try:
        db.init_db()
        token, expires_at = create_pairing_token(
            db, dolibarr_user_id, telegram_id
        )
    finally:
        db.close()

    name = " ".join(
        p for p in (user.get("firstname"), user.get("lastname")) if p
    ).strip() or user.get("login") or f"ID {dolibarr_user_id}"

    await update.message.reply_text(
        "🔐 LIEN TELEGRAM SÉCURISÉ\n\n"
        f"Utilisateur Dolibarr : {dolibarr_user_id}\n"
        f"Nom : {name}\n"
        f"Login : {user.get('login') or '—'}\n\n"
        f"Jeton :\n`{token}`\n\n"
        f"⏱ Validité : {PAIRING_TTL_MINUTES} minutes\n"
        "⚠️ Jeton à usage unique.\n"
        "Transmettez ce jeton uniquement à l'utilisateur concerné.",
        parse_mode="Markdown",
    )


async def link_command(update, context):
    if len(context.args) != 1:
        await update.message.reply_text("Usage : /lier <JETON>")
        return

    telegram_id = str(update.effective_user.id)
    username = update.effective_user.username or ""
    db = DatabaseManager()
    try:
        db.init_db()
        ok, result = consume_pairing_token(
            db, context.args[0], telegram_id, username
        )
    finally:
        db.close()

    if not ok:
        await update.message.reply_text(f"❌ {result}")
        return

    sync_db = DatabaseManager()
    try:
        sync_ok, sync_msg = sync_from_dolibarr(DolibarrClient(), sync_db)
    finally:
        sync_db.close()

    if not sync_ok:
        await update.message.reply_text(
            "⚠️ Compte lié, mais la synchronisation des rôles Dolibarr a échoué.\n"
            f"{sync_msg}\n\nRelancez /sync_roles."
        )
        return

    try:
        from modules.roles import refresh_command_menu
        await refresh_command_menu(context.bot, telegram_id)
    except Exception:
        pass

    name = " ".join(
        p for p in (result.get("firstname"), result.get("lastname")) if p
    ).strip() or result.get("login") or f"Dolibarr {result['dolibarr_user_id']}"

    await update.message.reply_text(
        "✅ Compte Telegram lié avec succès.\n\n"
        f"Dolibarr ID : {result['dolibarr_user_id']}\n"
        f"Nom : {name}\n"
        f"Login : {result.get('login') or '—'}\n\n"
        "Les permissions Telegram sont désormais calculées depuis "
        "les groupes métier Dolibarr."
    )
