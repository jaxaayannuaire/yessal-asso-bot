"""Module Caisse & Trésorerie.

Dolibarr reste le référentiel financier. DuckDB ne conserve ici que l'état
technique des demandes, l'idempotence et l'audit du bot.
"""

import logging
import os
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from core.auth import BOARD_ROLES, ROLE_PRESIDENT, ROLE_SUPER_ADMIN, ROLE_TRESORIER, AuthManager
from core.db import DatabaseManager
from services.dolibarr_api import DolibarrClient

logger = logging.getLogger(__name__)

CASH_WRITE_ROLES = frozenset({ROLE_SUPER_ADMIN, ROLE_PRESIDENT, ROLE_TRESORIER})
DEFAULT_PAYMENT_TYPE = os.getenv("DOLIBARR_CASH_PAYMENT_TYPE", "LIQ")
APPROVAL_THRESHOLD = Decimal(os.getenv("CASH_PRESIDENT_APPROVAL_THRESHOLD", "100000"))


def _parse_amount(value):
    try:
        amount = Decimal(str(value).replace(" ", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
    if amount <= 0:
        return None
    return amount.quantize(Decimal("0.01"))


def _format_amount(value):
    amount = Decimal(str(value))
    return f"{amount:,.2f}".replace(",", " ").replace(".", ",")


def _parse_cash_command(context):
    """Format: /entree 5000 1 Cotisation mensuelle"""
    if len(context.args) < 3:
        return None, "Usage : /entree <montant> <compte_id> <libellé>"
    amount = _parse_amount(context.args[0])
    if amount is None:
        return None, "❌ Montant invalide. Exemple : 5000"
    try:
        account_id = int(context.args[1])
    except ValueError:
        return None, "❌ ID de compte invalide. Utilisez /caisse pour voir les comptes."
    label = " ".join(context.args[2:]).strip()
    if not label:
        return None, "❌ Le libellé est obligatoire."
    if len(label) > 180:
        return None, "❌ Le libellé est trop long (180 caractères maximum)."
    return (amount, account_id, label), None


async def _require_cash_role(update):
    auth = AuthManager()
    user = auth.get_user(str(update.effective_user.id))
    if not user or not user[4] or user[2] not in CASH_WRITE_ROLES:
        await update.message.reply_text("⛔ Accès réservé au Bureau / Trésorier.")
        return None
    return user


async def caisse_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await _require_cash_role(update)
    if not user:
        return

    client = DolibarrClient()
    success, accounts = client.get_bank_accounts()
    if not success:
        await update.message.reply_text(f"❌ Impossible de lire les comptes Dolibarr : {accounts}")
        return
    if not accounts:
        await update.message.reply_text("ℹ️ Aucun compte bancaire/caisse disponible dans Dolibarr.")
        return

    lines = ["💰 *SITUATION DES CAISSES / COMPTES*", ""]
    total = Decimal("0")
    for account in accounts:
        account_id = account.get("id") or account.get("rowid")
        label = account.get("label") or account.get("ref") or f"Compte {account_id}"
        balance_ok, balance = client.get_bank_balance(account_id)
        if balance_ok:
            value = Decimal(str(balance or 0))
            total += value
            lines.append(f"• *{label}* — ID `{account_id}` : {_format_amount(value)} FCFA")
        else:
            lines.append(f"• *{label}* — ID `{account_id}` : ⚠️ {balance}")
    lines.extend(["", f"*Total : {_format_amount(total)} FCFA*", "", "Pour enregistrer :", "`/entree 5000 ID Compte libellé`", "`/sortie 5000 ID Compte libellé`"])
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def _create_pending_cash(update, context, direction):
    user = await _require_cash_role(update)
    if not user:
        return

    parsed, error = _parse_cash_command(context)
    if error:
        await update.message.reply_text(error)
        return
    amount, account_id, label = parsed

    client = DolibarrClient()
    ok, account = client.get_bank_account(account_id)
    if not ok:
        await update.message.reply_text(f"❌ Compte Dolibarr introuvable : {account}")
        return

    transaction_id = str(uuid.uuid4())
    idempotency_key = f"cash:{transaction_id}"
    status = "pending_confirmation"
    db = DatabaseManager()
    try:
        db.init_db()
        if not db.create_cash_transaction(
            transaction_id=transaction_id,
            idempotency_key=idempotency_key,
            direction=direction,
            account_id=str(account_id),
            amount=amount,
            label=label,
            payment_type=DEFAULT_PAYMENT_TYPE,
            transaction_date=date.today().isoformat(),
            requester_telegram_id=str(update.effective_user.id),
            requester_role=user[2],
            status=status,
        ):
            await update.message.reply_text("❌ Impossible de préparer l'opération.")
            return
        db.add_audit_event("cash.requested", str(update.effective_user.id), "cash_transaction", transaction_id, f"{direction}:{amount}:{account_id}")
    finally:
        db.close()

    account_label = account.get("label") or account.get("ref") or str(account_id)
    title = "➕ ENTRÉE" if direction == "in" else "➖ SORTIE"
    keyboard = [[
        InlineKeyboardButton("✅ Confirmer", callback_data=f"cash_confirm:{transaction_id}"),
        InlineKeyboardButton("❌ Annuler", callback_data=f"cash_cancel:{transaction_id}"),
    ]]
    text = (
        f"{title} À CONFIRMER\n\n"
        f"💰 Montant : *{_format_amount(amount)} FCFA*\n"
        f"🏦 Compte : *{account_label}* (ID {account_id})\n"
        f"📝 Libellé : {label}\n"
        f"📅 Date : {date.today().strftime('%d/%m/%Y')}\n\n"
        "Cette opération n'est pas encore écrite dans Dolibarr."
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def entree_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _create_pending_cash(update, context, "in")


async def sortie_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _create_pending_cash(update, context, "out")


async def cash_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        action, transaction_id = query.data.split(":", 1)
    except ValueError:
        return

    auth = AuthManager()
    actor_id = str(query.from_user.id)
    actor = auth.get_user(actor_id)
    if not actor or not actor[4]:
        await query.edit_message_text("⛔ Utilisateur inactif ou non autorisé.")
        return

    db = DatabaseManager()
    try:
        db.init_db()
        tx = db.get_cash_transaction_dict(transaction_id)
        if not tx:
            await query.edit_message_text("❌ Opération introuvable.")
            return

        if action == "cash_cancel":
            if actor_id != tx["requester_telegram_id"] and actor[2] not in BOARD_ROLES:
                await query.edit_message_text("⛔ Vous ne pouvez pas annuler cette opération.")
                return
            if tx["status"] not in {"pending_confirmation", "pending_approval"}:
                await query.edit_message_text(f"ℹ️ Opération déjà traitée : {tx['status']}.")
                return
            db.update_cash_transaction(transaction_id, status="cancelled", rejection_reason="Annulée depuis Telegram")
            db.add_audit_event("cash.cancelled", actor_id, "cash_transaction", transaction_id, "cancelled")
            await query.edit_message_text("❌ Opération annulée. Aucune écriture n'a été faite dans Dolibarr.")
            return

        if action == "cash_approve":
            if actor[2] not in {ROLE_PRESIDENT, ROLE_SUPER_ADMIN}:
                await query.edit_message_text("⛔ Seul le Président ou le Super Admin peut valider cette dépense.")
                return
            if tx["status"] != "pending_approval":
                await query.edit_message_text(f"ℹ️ Opération déjà traitée : {tx['status']}.")
                return
            db.update_cash_transaction(transaction_id, status="approved", approved_by_telegram_id=actor_id)
            db.add_audit_event("cash.approved", actor_id, "cash_transaction", transaction_id, "approved")
            tx["approved_by_telegram_id"] = actor_id
            tx["status"] = "approved"
            result = await _post_transaction(tx, db)
            await query.edit_message_text(result)
            return

        if action != "cash_confirm":
            return
        if actor_id != tx["requester_telegram_id"] and actor[2] not in BOARD_ROLES:
            await query.edit_message_text("⛔ Vous ne pouvez pas confirmer cette opération.")
            return
        if tx["status"] != "pending_confirmation":
            await query.edit_message_text(f"ℹ️ Opération déjà traitée : {tx['status']}.")
            return

        amount = Decimal(str(tx["amount"]))
        if tx["direction"] == "out" and amount >= APPROVAL_THRESHOLD and actor[2] == ROLE_TRESORIER:
            db.update_cash_transaction(transaction_id, status="pending_approval")
            db.add_audit_event("cash.pending_approval", actor_id, "cash_transaction", transaction_id, str(amount))
            president_ids = [row[0] for row in db.get_user_ids_by_roles({ROLE_PRESIDENT, ROLE_SUPER_ADMIN})]
            if not president_ids:
                await query.edit_message_text("⚠️ Dépense enregistrée en attente, mais aucun Président/Super Admin actif n'est configuré.")
                return
            await query.edit_message_text("⏳ Dépense soumise à validation du Président / Super Admin.")
            approval_text = (
                "🔐 *VALIDATION DE DÉPENSE REQUISE*\n\n"
                f"💰 { _format_amount(amount) } FCFA\n"
                f"🏦 Compte : {tx['account_id']}\n"
                f"📝 {tx['label']}\n"
                f"👤 Demandeur Telegram : {tx['requester_telegram_id']}\n\n"
                "Une confirmation écrira l'opération dans Dolibarr."
            )
            keyboard = [[InlineKeyboardButton("✅ APPROUVER", callback_data=f"cash_approve:{transaction_id}"), InlineKeyboardButton("❌ REFUSER", callback_data=f"cash_cancel:{transaction_id}")]]
            for president_id in president_ids:
                try:
                    await context.bot.send_message(president_id, approval_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
                except Exception:
                    logger.exception("Impossible d'envoyer la demande de validation au %s", president_id)
            return

        result = await _post_transaction(tx, db)
        await query.edit_message_text(result)
    finally:
        db.close()


async def _post_transaction(tx, db):
    """Écrit une seule fois dans Dolibarr, puis marque l'opération comme postée."""
    if tx["status"] == "posted":
        return f"✅ Opération déjà enregistrée dans Dolibarr (ligne {tx['dolibarr_line_id']})."

    client = DolibarrClient()
    amount = Decimal(str(tx["amount"]))
    signed_amount = amount if tx["direction"] == "in" else -amount
    marker = f"[YAB:{tx['id']}]"
    existing_ok, existing_lines = client.get_bank_lines(int(tx["account_id"]))
    if existing_ok and isinstance(existing_lines, list):
        for line in existing_lines:
            if marker in str(line.get("label", "")):
                existing_id = line.get("id") or line.get("rowid")
                db.update_cash_transaction(tx["id"], status="posted", dolibarr_line_id=str(existing_id or ""))
                db.add_audit_event("cash.posted_existing", tx["requester_telegram_id"], "cash_transaction", tx["id"], f"dolibarr_line_id={existing_id}")
                return f"✅ *Opération déjà présente dans Dolibarr.*\n\n🆔 Ligne Dolibarr : {existing_id}"

    success, line_id = client.add_bank_line(
        account_id=int(tx["account_id"]),
        transaction_date=tx["transaction_date"],
        payment_type=tx["payment_type"],
        label=f"{tx['label']} {marker}",
        amount=signed_amount,
    )
    if not success:
        db.update_cash_transaction(tx["id"], status="post_failed", rejection_reason=str(line_id))
        db.add_audit_event("cash.post_failed", tx["requester_telegram_id"], "cash_transaction", tx["id"], str(line_id))
        return f"❌ Écriture Dolibarr échouée : {line_id}\n\nL'opération reste conservée dans l'audit technique."

    db.update_cash_transaction(tx["id"], status="posted", dolibarr_line_id=str(line_id))
    db.add_audit_event("cash.posted", tx["requester_telegram_id"], "cash_transaction", tx["id"], f"dolibarr_line_id={line_id}")
    verb = "entrée" if tx["direction"] == "in" else "sortie"
    return f"✅ *{verb.capitalize()} enregistrée dans Dolibarr.*\n\n💰 { _format_amount(amount) } FCFA\n🏦 Compte : {tx['account_id']}\n📝 {tx['label']}\n🆔 Ligne Dolibarr : {line_id}"
