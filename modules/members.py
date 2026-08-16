from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import ContextTypes

from core.auth import AuthManager, BOARD_ROLES
from core.db import DatabaseManager
from services.dolibarr_api import DolibarrClient

NEW_MEMBER_DAYS = 30


def _member_is_active(member):
    status = member.get("statut")
    if status is None:
        status = member.get("status", 0)
    try:
        return int(status) == 1
    except (TypeError, ValueError):
        return str(status).lower() in {"true", "active"}


def _member_created_at(member):
    value = member.get("date_creation")
    if value in (None, ""):
        value = member.get("datec")
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    try:
        return datetime.fromisoformat(
            str(value).strip().replace("Z", "+00:00")
        ).astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def build_members_overview(members, member_types=None, now=None, days=NEW_MEMBER_DAYS):
    members = members or []
    member_types = member_types or []
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    labels = {}
    ordered = []
    for item in member_types:
        type_id = item.get("id", item.get("rowid"))
        label = item.get("label", item.get("name", item.get("nom", "")))
        if type_id is not None and label:
            key = str(type_id)
            labels[key] = str(label)
            if key not in ordered:
                ordered.append(key)

    counts = {key: 0 for key in ordered}
    active = 0
    new_members = 0

    for member in members:
        if _member_is_active(member):
            active += 1

        created = _member_created_at(member)
        if created and cutoff <= created <= now:
            new_members += 1

        type_id = member.get("typeid", member.get("type_id"))
        type_id = "" if type_id is None else str(type_id)

        if type_id not in counts:
            labels[type_id] = str(
                member.get("type") or member.get("type_label") or "Type inconnu"
            )
            counts[type_id] = 0
            ordered.append(type_id)

        counts[type_id] += 1

    return {
        "total": len(members),
        "active": active,
        "inactive": len(members) - active,
        "new_30_days": new_members,
        "by_type": [
            {"id": key, "label": labels[key], "count": counts[key]}
            for key in ordered
        ],
    }


def format_members_overview(stats):
    lines = [
        "👥 ADHÉRENTS YESSAL ASSO",
        "",
        "📊 Vue générale",
        "",
        f"👥 Total : {stats['total']}",
        f"🟢 Actifs : {stats['active']}",
        f"🔴 Inactifs : {stats['inactive']}",
        f"🆕 Nouveaux (30 jours) : {stats['new_30_days']}",
        "",
        "📋 Par type",
    ]
    lines.extend(
        f"• {item['label']} : {item['count']}" for item in stats["by_type"]
    )
    return "\n".join(lines)


async def members_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auth = AuthManager()
    user = auth.get_user(str(update.effective_user.id))
    if not user or user[2] not in BOARD_ROLES:
        await update.message.reply_text("⛔ Accès refusé.")
        return

    await update.message.reply_text("⏳ Chargement des adhérents depuis Dolibarr...")

    client = DolibarrClient()
    success, members = client.get_members()
    if not success:
        await update.message.reply_text(f"❌ Erreur : {members}")
        return

    type_success, member_types = client.get_dolibarr_member_types()
    if not type_success:
        member_types = []

    stats = build_members_overview(members, member_types)
    await update.message.reply_text(format_members_overview(stats))


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
