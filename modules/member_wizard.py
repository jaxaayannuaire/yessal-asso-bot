"""17A.7.1 - Wizard interactif d'inscription d'un adhérent.

Le Wizard collecte les informations sans créer quoi que ce soit dans Dolibarr.
La création n'est déclenchée qu'après le bouton VALIDER.

Le moteur générique est fourni par core.wizard.
"""

from datetime import date, datetime
import html
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core.auth import AuthManager
from core.db import DatabaseManager
from core.permissions import (
    ROLE_BUREAU,
    ROLE_PRESIDENT,
    ROLE_SUPER_ADMIN,
    ROLE_TRESORIER,
    ensure_schema,
    sync_from_dolibarr,
)
from services.dolibarr_api import DolibarrClient
from core.wizard import WizardDefinition, WizardManager, WizardStep


REGISTRATION_ROLES = frozenset({
    ROLE_SUPER_ADMIN,
    ROLE_PRESIDENT,
    ROLE_BUREAU,
    ROLE_TRESORIER,
})

DEFAULT_MEMBER_EMAIL = os.getenv("DEFAULT_MEMBER_EMAIL", "email@email.com")
DEFAULT_MEMBER_TYPE_ID = os.getenv("DEFAULT_MEMBER_TYPE_ID", "1")
DEFAULT_MEMBER_MORPHY = os.getenv("DEFAULT_MEMBER_MORPHY", "mor")


def _actor_id(update):
    return str(update.effective_user.id)


def _authorized(update):
    auth = AuthManager()
    return any(
        auth.has_role(_actor_id(update), {role})
        for role in REGISTRATION_ROLES
    )


def _required_text(value):
    value = value.strip()
    if not value:
        raise ValueError("Cette information est obligatoire.")
    return value


def _phone(value):
    value = value.strip().replace(" ", "").replace("-", "").replace(".", "")
    if not value:
        raise ValueError("Le numéro de téléphone est obligatoire.")
    if value.startswith("+221"):
        value = value[4:]
    if not value.isdigit() or len(value) != 9:
        raise ValueError("Entrez un numéro sénégalais valide à 9 chiffres.")
    return value


def _email(value):
    value = value.strip()
    if not value or value.upper() == "X":
        return DEFAULT_MEMBER_EMAIL
    if "@" not in value or "." not in value.split("@")[-1]:
        raise ValueError("Email invalide. Utilisez X si l'adhérent n'en possède pas.")
    return value


def _date(value):
    value = value.strip()
    if not value:
        raise ValueError("La date est obligatoire.")
    try:
        parsed = datetime.strptime(value, "%d/%m/%Y")
    except ValueError as exc:
        raise ValueError("Format attendu : JJ/MM/AAAA et date valide.") from exc
    return parsed.strftime("%Y-%m-%d")


def _type_keyboard(_data):
    client = DolibarrClient()
    ok, data = client.get_dolibarr_member_types()
    if not ok:
        # Le choix par défaut reste disponible si l'API de types est indisponible.
        return InlineKeyboardMarkup([[
            InlineKeyboardButton(
                f"👤 Membre Actif ({DEFAULT_MEMBER_TYPE_ID})",
                callback_data=f"wiz:choose:type_id:{DEFAULT_MEMBER_TYPE_ID}",
            )
        ]])

    values = data if isinstance(data, list) else (
        data.get("data", []) if isinstance(data, dict) else []
    )
    buttons = []
    for item in values:
        if not isinstance(item, dict):
            continue
        iid = item.get("id", item.get("rowid"))
        label = item.get("label", item.get("name", iid))
        status = item.get("statut", item.get("status", 1))
        try:
            active = int(status) != 0
        except (TypeError, ValueError):
            active = bool(status)
        if str(iid).isdigit() and active:
            buttons.append([InlineKeyboardButton(
                str(label),
                callback_data=f"wiz:choose:type_id:{iid}",
            )])

    if not buttons:
        buttons = [[InlineKeyboardButton(
            f"👤 Membre Actif ({DEFAULT_MEMBER_TYPE_ID})",
            callback_data=f"wiz:choose:type_id:{DEFAULT_MEMBER_TYPE_ID}",
        )]]
    return InlineKeyboardMarkup(buttons)


def _default_date_keyboard(_data):
    today = date.today().strftime("%d/%m/%Y")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"📅 Aujourd'hui — {today}",
            callback_data=f"wiz:choose:date_adhesion:{today}",
        )],
    ])


def _sex_keyboard(_data):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("👨 Homme", callback_data="wiz:choose:sex:H"),
        InlineKeyboardButton("👩 Femme", callback_data="wiz:choose:sex:F"),
    ]])


def _summary(data):
    sex = {"H": "Homme", "F": "Femme"}.get(data.get("sex"), data.get("sex", "—"))
    email_default = data.get("email") == DEFAULT_MEMBER_EMAIL
    email_value = data.get("email", "—")
    email_label = (
        f"{email_value} (défaut)" if email_default else email_value
    )
    values = {
        "lastname": html.escape(str(data.get("lastname", "—"))),
        "firstname": html.escape(str(data.get("firstname", "—"))),
        "sex": html.escape(str(sex)),
        "phone": html.escape(str(data.get("phone", "—"))),
        "email": html.escape(str(email_label)),
        "type_id": html.escape(str(data.get("type_id", DEFAULT_MEMBER_TYPE_ID))),
        "date_adhesion": html.escape(str(data.get("date_adhesion", "—"))),
    }

    return (
        "🔎 <b>VÉRIFICATION — NOUVEL ADHÉRENT</b>\n\n"
        f"👤 Nom : <b>{values['lastname']}</b>\n"
        f"👤 Prénom : <b>{values['firstname']}</b>\n"
        f"🚻 Sexe : <b>{values['sex']}</b>\n"
        f"📱 Téléphone : <b>{values['phone']}</b>\n"
        f"📧 Email : <b>{values['email']}</b>\n"
        f"🏷 Type d'adhérent : <b>{values['type_id']}</b>\n"
        f"📅 Date d'adhésion : <b>{values['date_adhesion']}</b>\n"
        "🧍 Nature : <b>Personne physique</b>\n\n"
        "Aucune écriture Dolibarr n'a encore été effectuée.\n"
        "Choisissez une action :"
    )


async def _on_confirm(update, context, data):
    """Création réelle dans Dolibarr, après confirmation explicite."""
    client = DolibarrClient()

    payload = {
        "morphy": DEFAULT_MEMBER_MORPHY,
        "typeid": int(data.get("type_id", DEFAULT_MEMBER_TYPE_ID)),
        "firstname": data["firstname"],
        "lastname": data["lastname"],
        "statut": 1,
        "email": data["email"],
        "phone": data["phone"],
        "gender": data["sex"],
    }

    ok, result = client.create_dolibarr_member(payload)
    if not ok:
        await update.effective_message.reply_text(
            f"❌ Création de l'adhérent impossible : {result}"
        )
        return

    member_id = None
    if isinstance(result, dict):
        member_id = result.get("id", result.get("rowid"))
    elif str(result).isdigit():
        member_id = str(result)

    db = DatabaseManager()
    try:
        ensure_schema(db)
        db.add_audit_event(
            "member_created_from_telegram_wizard",
            actor_telegram_id=_actor_id(update),
            entity_type="dolibarr_member",
            entity_id=str(member_id or ""),
            details=(
                f"{data['firstname']} {data['lastname']};"
                f"sex={data['sex']};phone={data['phone']};"
                f"email={data['email']};typeid={data['type_id']};"
                f"date_adhesion={data['date_adhesion']}"
            ),
        )
        sync_from_dolibarr(client, db)
    finally:
        db.close()

    await update.effective_message.reply_text(
        "✅ <b>ADHÉRENT ENREGISTRÉ</b>\n\n"
        f"Nom : {data['firstname']} {data['lastname']}\n"
        f"Sexe : {'Homme' if data['sex'] == 'H' else 'Femme'}\n"
        f"Téléphone : {data['phone']}\n"
        f"Email : {data['email']}\n"
        f"ID adhérent : <code>{member_id or result}</code>\n\n"
        "🔄 Dolibarr et le miroir ont été synchronisés.",
        parse_mode="HTML",
    )


WIZARD_DEFINITION = WizardDefinition(
    name="member_registration",
    title="👤 INSCRIPTION D'UN ADHÉRENT",
    steps=[
        WizardStep("lastname", "1/7 — Quel est le <b>nom de famille</b> ?",
                    parser=_required_text),
        WizardStep("firstname", "2/7 — Quel est le <b>prénom</b> ?",
                    parser=_required_text),
        WizardStep("sex", "3/7 — Sélectionnez le <b>sexe</b> :",
                    keyboard=_sex_keyboard),
        WizardStep("phone", "4/7 — 📱 Quel est le <b>numéro de téléphone</b> ?\n\n"
                    "Le téléphone est obligatoire.",
                    parser=_phone),
        WizardStep("email", "5/7 — 📧 Email ?\n\n"
                    "Vous pouvez répondre <b>X</b> si l'adhérent n'en a pas.",
                    parser=_email),
        WizardStep("type_id", "6/7 — 🏷 Sélectionnez le <b>type d'adhérent</b> :",
                    keyboard=_type_keyboard),
        WizardStep(
            "date_adhesion",
            "7/7 — 📅 Date d'adhésion ?\n\n"
            "La date du jour est proposée par défaut.",
            parser=_date,
            keyboard=_default_date_keyboard,
        ),
    ],
    summary=_summary,
    on_confirm=_on_confirm,
)


wizard_manager = WizardManager({"member_registration": WIZARD_DEFINITION})


async def inscrire_membre_wizard_command(update, context):
    if not _authorized(update):
        await update.message.reply_text(
            "⛔ Réservé au Président, Bureau ou Trésorier."
        )
        return
    await wizard_manager.start(update, context, "member_registration")


async def wizard_text_router(update, context):
    return await wizard_manager.handle_text(update, context)


async def wizard_callback_router(update, context):
    return await wizard_manager.handle_callback(update, context)
