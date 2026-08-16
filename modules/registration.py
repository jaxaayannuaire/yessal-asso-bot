"""Phase 17A.6 - inscription associative et création d'opérateurs.

Règles:
- Dolibarr reste la source de vérité.
- Président, Bureau et Trésorier peuvent créer contacts, tiers et adhérents.
- Seul le Super Admin peut créer un compte opérateur Dolibarr et lui attribuer
  un groupe métier privilégié.
- Un opérateur créé peut ensuite utiliser /lier avec le jeton généré.
- Les écritures sont auditées dans DuckDB.
"""
import secrets
import unicodedata
import re
from html import escape

from core.auth import AuthManager
from core.db import DatabaseManager
from core.permissions import (
    ROLE_BUREAU,
    ROLE_PRESIDENT,
    ROLE_SUPER_ADMIN,
    ROLE_TRESORIER,
    ROLE_GROUP_NAMES,
    ensure_schema,
    find_group_by_role,
    sync_from_dolibarr,
)
from services.dolibarr_api import DolibarrClient
from modules.telegram_link import create_pairing_token

REGISTRATION_ROLES = frozenset({
    ROLE_SUPER_ADMIN,
    ROLE_PRESIDENT,
    ROLE_BUREAU,
    ROLE_TRESORIER,
})

OPERATOR_ROLES = frozenset({
    ROLE_PRESIDENT,
    ROLE_BUREAU,
    ROLE_TRESORIER,
    "admin",
    "membre",
})

def _actor_id(update):
    return str(update.effective_user.id)

def _authorized(update):
    auth = AuthManager()
    return any(auth.has_role(_actor_id(update), {role}) for role in REGISTRATION_ROLES)

def _super_admin(update):
    return AuthManager().is_super_admin(_actor_id(update))

def _parts(context, minimum, maximum=None):
    if not context.args:
        return None
    raw = " ".join(context.args).strip()
    parts = [item.strip() for item in raw.split(";")]
    if len(parts) < minimum or (maximum is not None and len(parts) > maximum):
        return None
    return parts

def _usage(command, fields):
    return f"Usage : /{command} " + ";".join(fields)

def _safe_login(firstname, lastname, requested=""):
    if requested.strip():
        return requested.strip().lower()
    raw = unicodedata.normalize("NFKD", f"{firstname}{lastname}")
    raw = raw.encode("ascii", "ignore").decode("ascii")
    raw = re.sub(r"[^a-zA-Z0-9]+", "", raw).lower()
    return (raw[:28] or "operateur")

def _operator_confirmation_message(firstname, lastname, login, user_id, member_id, role, token):
    """Construit le message final envoyé après création d'un opérateur.

    HTML est utilisé plutôt que Markdown afin d'éviter les erreurs Telegram
    provoquées par des valeurs dynamiques contenant notamment des underscores.
    """
    role_label = ROLE_GROUP_NAMES.get(role, role)
    return (
        "👤 <b>OPÉRATEUR YESSAL CRÉÉ</b>\n\n"
        f"Nom : {escape(f'{firstname} {lastname}')}\n"
        f"Login Dolibarr : <code>{escape(login)}</code>\n"
        f"Utilisateur Dolibarr : <code>{escape(str(user_id))}</code>\n"
        f"Adhérent actif : <code>{escape(str(member_id or 'créé'))}</code>\n"
        f"Rôle : <code>{escape(str(role_label))}</code>\n\n"
        "🔐 <b>LIEN TELEGRAM</b>\n"
        f"Jeton : <code>{escape(token)}</code>\n"
        "Validité : 10 minutes\n"
        "Usage unique.\n\n"
        "L'opérateur doit envoyer au bot :\n"
        f"<code>/lier {escape(token)}</code>"
    )


def _extract_id(result):
    if isinstance(result, (int, str)) and str(result).isdigit():
        return str(result)
    if isinstance(result, dict):
        for key in ("id", "rowid"):
            value = result.get(key)
            if value is not None and str(value).isdigit():
                return str(value)
        success = result.get("success")
        if isinstance(success, dict):
            for key in ("id", "rowid"):
                value = success.get(key)
                if value is not None and str(value).isdigit():
                    return str(value)
    return None

def _member_type_id(client, requested=None):
    if requested and str(requested).isdigit():
        return int(requested)
    ok, data = client.get_dolibarr_member_types()
    if not ok:
        return False, f"Impossible de lire les types d'adhérents : {data}"
    values = data if isinstance(data, list) else data.get("data", []) if isinstance(data, dict) else []
    active = []
    for item in values:
        if not isinstance(item, dict):
            continue
        iid = item.get("id", item.get("rowid"))
        label = item.get("label", item.get("name", item.get("nom", "")))
        status = item.get("statut")
        if status is None:
            status = item.get("status", 1)
        if status is None:
            status = 1
        try:
            enabled = int(status) != 0
        except (TypeError, ValueError):
            enabled = bool(status)
        if str(iid).isdigit() and enabled:
            active.append((int(iid), str(label or iid)))
    if len(active) == 1:
        return True, active[0][0]
    if not active:
        return False, "Aucun type d'adhérent actif trouvé dans Dolibarr."
    return False, "Plusieurs types d'adhérents existent : " + ", ".join(
        f"{iid}={label}" for iid, label in active
    ) + ". Ajoutez le typeid en dernier argument."

async def inscrire_membre_command(update, context):
    if not _authorized(update):
        await update.message.reply_text("⛔ Réservé au Président, Bureau ou Trésorier.")
        return
    parts = _parts(context, 3, 5)
    if not parts:
        await update.message.reply_text(_usage(
            "inscrire_membre",
            ["NOM", "PRENOM", "TELEPHONE", "EMAIL", "TYPEID(optional)"]
        ))
        return
    lastname, firstname, phone = parts[:3]
    email = parts[3] if len(parts) >= 4 else ""
    requested_type = parts[4] if len(parts) >= 5 else None
    client = DolibarrClient()
    type_result = _member_type_id(client, requested_type)

    if isinstance(type_result, tuple):
        ok_type, type_value = type_result
        if not ok_type:
            await update.message.reply_text(f"❌ {type_value}")
            return
    else:
        ok_type = True
        type_value = type_result
        
    if not ok_type:
        await update.message.reply_text(f"❌ {type_value}")
        return
    payload = {
        "morphy": "mor",
        "typeid": type_value,
        "firstname": firstname,
        "lastname": lastname,
        "statut": 1,
    }
    if email:
        payload["email"] = email
    if phone:
        payload["phone"] = phone
    ok, result = client.create_dolibarr_member(payload)
    if not ok:
        await update.message.reply_text(f"❌ Création de l'adhérent impossible : {result}")
        return
    member_id = _extract_id(result)
    db = DatabaseManager()
    try:
        ensure_schema(db)
        db.add_audit_event(
            "member_created_from_telegram",
            actor_telegram_id=_actor_id(update),
            entity_type="dolibarr_member",
            entity_id=member_id,
            details=f"{firstname} {lastname};phone={phone}",
        )
    finally:
        db.close()
    await update.message.reply_text(
        "✅ ADHÉRENT ACTIF ENREGISTRÉ\n\n"
        f"Nom : {firstname} {lastname}\n"
        f"Téléphone : {phone or '—'}\n"
        f"ID Dolibarr : {member_id or result}"
    )

async def creer_contact_command(update, context):
    if not _authorized(update):
        await update.message.reply_text("⛔ Réservé au Président, Bureau ou Trésorier.")
        return
    parts = _parts(context, 2, 5)
    if not parts:
        await update.message.reply_text(_usage(
            "creer_contact",
            ["NOM", "PRENOM", "TELEPHONE(optional)", "EMAIL(optional)", "TIERSID(optional)"]
        ))
        return
    lastname, firstname = parts[:2]
    phone = parts[2] if len(parts) >= 3 else ""
    email = parts[3] if len(parts) >= 4 else ""
    thirdparty_id = parts[4] if len(parts) >= 5 else ""
    payload = {
        "lastname": lastname,
        "firstname": firstname,
    }
    if phone:
        payload["phone_mobile"] = phone
    if email:
        payload["email"] = email
        payload["mail"] = email
    if thirdparty_id:
        if not thirdparty_id.isdigit():
            await update.message.reply_text("❌ L'ID tiers doit être numérique.")
            return
        payload["socid"] = thirdparty_id
    ok, result = DolibarrClient().create_dolibarr_contact(payload)
    if not ok:
        await update.message.reply_text(f"❌ Création du contact impossible : {result}")
        return
    contact_id = _extract_id(result)
    db = DatabaseManager()
    try:
        ensure_schema(db)
        db.add_audit_event(
            "contact_created_from_telegram",
            actor_telegram_id=_actor_id(update),
            entity_type="dolibarr_contact",
            entity_id=contact_id,
            details=f"{firstname} {lastname};phone={phone}",
        )
    finally:
        db.close()
    await update.message.reply_text(
        "✅ CONTACT ENREGISTRÉ DANS DOLIBARR\n\n"
        f"Nom : {firstname} {lastname}\nID Dolibarr : {contact_id or result}"
    )

async def creer_tiers_command(update, context):
    if not _authorized(update):
        await update.message.reply_text("⛔ Réservé au Président, Bureau ou Trésorier.")
        return
    parts = _parts(context, 1, 3)
    if not parts:
        await update.message.reply_text(_usage(
            "creer_tiers", ["NOM", "TELEPHONE(optional)", "EMAIL(optional)"]
        ))
        return
    name = parts[0]
    phone = parts[1] if len(parts) >= 2 else ""
    email = parts[2] if len(parts) >= 3 else ""
    payload = {"name": name, "client": 0, "fournisseur": 0}
    if phone:
        payload["phone"] = phone
    if email:
        payload["email"] = email
    ok, result = DolibarrClient().create_dolibarr_thirdparty(payload)
    if not ok:
        await update.message.reply_text(f"❌ Création du tiers impossible : {result}")
        return
    thirdparty_id = _extract_id(result)
    db = DatabaseManager()
    try:
        ensure_schema(db)
        db.add_audit_event(
            "thirdparty_created_from_telegram",
            actor_telegram_id=_actor_id(update),
            entity_type="dolibarr_thirdparty",
            entity_id=thirdparty_id,
            details=f"name={name}",
        )
    finally:
        db.close()
    await update.message.reply_text(
        "✅ TIERS ENREGISTRÉ DANS DOLIBARR\n\n"
        f"Nom : {name}\nID Dolibarr : {thirdparty_id or result}"
    )

async def creer_operateur_command(update, context):
    """Crée un utilisateur Dolibarr + adhérent actif + groupe métier + jeton Telegram."""
    if not _super_admin(update):
        await update.message.reply_text("⛔ Réservé au Super Admin.")
        return
    parts = _parts(context, 5, 7)
    if not parts:
        await update.message.reply_text(_usage(
            "creer_operateur",
            ["NOM", "PRENOM", "LOGIN", "EMAIL", "TELEPHONE", "ROLE", "TYPEID(optional)"]
        ))
        return
    lastname, firstname, requested_login, email, phone = parts[:5]
    role = parts[5].strip().lower() if len(parts) >= 6 else ROLE_TRESORIER
    requested_type = parts[6] if len(parts) >= 7 else None
    if role not in OPERATOR_ROLES:
        await update.message.reply_text(
            "❌ Rôle invalide. Valeurs : president, bureau, tresorier, admin, membre."
        )
        return

    client = DolibarrClient()
    type_result = _member_type_id(client, requested_type)

    if isinstance(type_result, tuple):
        ok_type, type_value = type_result
        if not ok_type:
            await update.message.reply_text(f"❌ {type_value}")
            return
    else:
        ok_type = True
        type_value = type_result
    if not ok_type:
        await update.message.reply_text(f"❌ {type_value}")
        return

    login = _safe_login(firstname, lastname, requested_login)
    # Le mot de passe n'est pas demandé dans Telegram : l'opérateur est
    # destiné au bot. Il pourra définir son accès Dolibarr ultérieurement.
    user_payload = {
        "login": login,
        "firstname": firstname,
        "lastname": lastname,
        "statut": 1,
        "status": 1,
        "admin": 0,
        "employee": 1,
    }
    if email:
        user_payload["email"] = email
    if phone:
        user_payload["office_phone"] = phone

    ok_user, user_result = client.create_dolibarr_user(user_payload)
    if not ok_user:
        await update.message.reply_text(f"❌ Création du compte Dolibarr impossible : {user_result}")
        return
    user_id = _extract_id(user_result)
    if not user_id:
        await update.message.reply_text(
            f"⚠️ Dolibarr a créé le compte mais l'ID n'a pas été reconnu : {user_result}"
        )
        return

    member_payload = {
        "morphy": "mor",
        "typeid": type_value,
        "firstname": firstname,
        "lastname": lastname,
        "statut": 1,
    }
    if email:
        member_payload["email"] = email
    if phone:
        member_payload["phone"] = phone

    ok_member, member_result = client.create_dolibarr_member(member_payload)
    if not ok_member:
        # Nettoyage best-effort : le compte créé sans adhérent ne doit pas
        # rester silencieusement orphelin.
        client.delete_dolibarr_user(user_id)
        await update.message.reply_text(
            "❌ Création de l'adhérent impossible. "
            "Le compte utilisateur Dolibarr créé pour cette opération a été "
            f"supprimé si les droits API le permettent.\n\n{member_result}"
        )
        return
    member_id = _extract_id(member_result)

    if not member_id:
        client.delete_dolibarr_user(user_id)
        await update.message.reply_text(
            "❌ L'adhérent a été créé mais son ID n'a pas pu être déterminé. "
            "Le compte utilisateur a été supprimé si possible."
        )
        return

    ok_link, link_result = client.link_dolibarr_user_to_member(
        user_id,
        member_id,
    )

    if not ok_link:
        client.delete_dolibarr_member(member_id)
        client.delete_dolibarr_user(user_id)

        await update.message.reply_text(
            "❌ Impossible de lier l'utilisateur Dolibarr à son adhérent.\n"
            "Les objets créés ont été supprimés si les droits API le permettent.\n\n"
            f"{link_result}"
        )
        return

    db = DatabaseManager()
    try:
        ensure_schema(db)
        sync_ok, sync_msg = sync_from_dolibarr(client, db)
        if not sync_ok:
            await update.message.reply_text(
                "⚠️ Utilisateur et adhérent créés dans Dolibarr, mais le miroir "
                f"n'a pas pu être synchronisé : {sync_msg}"
            )
            return
        group = find_group_by_role(db, role)
        if not group:
            await update.message.reply_text(
                f"⚠️ Compte Dolibarr {user_id} et adhérent {member_id} créés, "
                f"mais le groupe {ROLE_GROUP_NAMES.get(role, role)} est introuvable. "
                "Utilisez /creer_groupes puis attribuez le rôle."
            )
            return
        ok_group, group_result = client.add_user_to_group(user_id, group[0])
        if not ok_group:
            await update.message.reply_text(
                f"⚠️ Compte {user_id} et adhérent {member_id} créés, "
                f"mais attribution du groupe impossible : {group_result}"
            )
            return
        sync_ok, sync_msg = sync_from_dolibarr(client, db)
        if not sync_ok:
            await update.message.reply_text(
                "⚠️ Groupe attribué dans Dolibarr, mais synchronisation échouée : "
                f"{sync_msg}"
            )
            return

        token, expires_at = create_pairing_token(
            db, user_id, _actor_id(update)
        )
        db.add_audit_event(
            "operator_created_from_telegram",
            actor_telegram_id=_actor_id(update),
            entity_type="dolibarr_user",
            entity_id=user_id,
            details=(
                f"member_id={member_id};login={login};role={role};"
                f"expires_at={expires_at.isoformat()}"
            ),
        )
    finally:
        db.close()

    confirmation = _operator_confirmation_message(
        firstname, lastname, login, user_id, member_id, role, token
    )
    await update.message.reply_text(confirmation, parse_mode="HTML")
