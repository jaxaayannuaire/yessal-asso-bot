from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from core.auth import AuthManager

MEMBER_FILTERS = (
    ("lastname", "Nom"), ("firstname", "Prénom"),
    ("ref", "Référence"), ("phone", "Téléphone"),
    ("phone_mobile", "WhatsApp"), ("email", "Email"),
    ("town", "Ville"), ("gender", "Sexe"),
    ("typeid", "Type d’adhérent"), ("adhesion_month", "Mois d’adhésion"),
    ("adhesion_year", "Année d’adhésion"), ("fonction", "Fonction"),
    ("responsabilite", "Responsabilité"), ("tag", "Tag / catégorie"),
)

SEARCH_TYPES = (
    ("members", "👥 Adhérents", "total_members"),
    ("contacts", "📇 Contacts", "total_contacts"),
    ("contributions", "💰 Cotisations", "total_contributions"),
    ("cash", "💵 Caisse", "total_cash"),
    ("products", "📦 Produits", "total_products"),
    ("services", "🛠️ Services", "total_services"),
    ("invoices", "🧾 Factures", "total_invoices"),
    ("documents", "📁 Documents", "total_documents"),
    ("thirdparties", "🏢 Tiers", "total_thirdparties"),
    ("users", "👤 Utilisateurs", "total_users"),
    ("contracts", "📑 Contrats", "total_contracts"),
    ("banks", "🏦 Banques", "total_banks"),
)


def _format_amount(value):
    try:
        return f"{int(value):,}".replace(",", " ") + " FCFA"
    except (TypeError, ValueError):
        return f"{value} FCFA"


def _get_search_stats():
    return {
        "total_contacts": 0, "total_members": 0, "total_contributions": 0,
        "total_cash": 0, "total_products": 0, "total_services": 0,
        "total_invoices": 0, "total_documents": 0, "total_thirdparties": 0,
        "total_users": 0, "total_contracts": 0, "total_banks": 0,
    }


def _build_search_text(stats):
    stats = {**_get_search_stats(), **(stats or {})}
    return (
        "🔎 *RECHERCHE YESSAL ASSO* 🔎\n\n"
        "Recherchez, consultez et gérez les informations de votre association.\n\n"
        f"👥 *Contacts :* {stats['total_contacts']}\n"
        f"🏷️ *Adhérents :* {stats['total_members']}\n"
        f"💰 *Cotisations :* {_format_amount(stats['total_contributions'])}\n\n"
        "🚀 *Recherches rapides :*"
    )


def _build_keyboard(stats):
    stats = {**_get_search_stats(), **(stats or {})}
    rows = []
    for i in range(0, len(SEARCH_TYPES), 2):
        row = []
        for callback, label, stat_key in SEARCH_TYPES[i:i + 2]:
            row.append(InlineKeyboardButton(
                f"{label} ({stats.get(stat_key, 0)})",
                callback_data=f"search:type:{callback}",
            ))
        rows.append(row)
    rows.append([InlineKeyboardButton("❌ Fermer", callback_data="search:close")])
    return InlineKeyboardMarkup(rows)


INTERACTIVE_MEMBER_FILTERS = {
    "lastname", "firstname", "ref", "phone", "phone_mobile",
}

PENDING_FILTER_KEY = "search_pending_filter"
FILTERS_DATA_KEY = "search_filters"


def _get_member_filters(context):
    data = context.user_data.get(FILTERS_DATA_KEY)
    if isinstance(data, dict):
        return data
    filters = {}
    context.user_data[FILTERS_DATA_KEY] = filters
    return filters


def _member_filter_label(key):
    return dict(MEMBER_FILTERS).get(key, key)


async def prompt_member_filter(update, context, key):
    query = update.callback_query
    await query.answer()
    context.user_data[PENDING_FILTER_KEY] = key
    await query.edit_message_text(
        text=(
            f"✏️ *{_member_filter_label(key)}*\n\n"
            "Envoyez maintenant la valeur recherchée.\n"
            "Exemple : `Diop`\n\n"
            "Envoyez `/annuler` pour abandonner."
        ),
        parse_mode="Markdown",
    )


async def handle_member_filter_input(update, context):
    key = context.user_data.get(PENDING_FILTER_KEY)
    if key not in INTERACTIVE_MEMBER_FILTERS:
        return False

    if not update.message or not update.message.text:
        return False

    value = update.message.text.strip()
    if not value:
        await update.message.reply_text("⚠️ Valeur vide. Réessayez.")
        return True

    filters = _get_member_filters(context)
    filters[key] = value
    context.user_data.pop(PENDING_FILTER_KEY, None)

    await update.message.reply_text(
        text=build_member_filters_text(filters),
        reply_markup=build_member_filters_keyboard(),
        parse_mode="Markdown",
    )
    return True


async def cancel_member_filter_input(update, context):
    if context.user_data.pop(PENDING_FILTER_KEY, None) is None:
        return False
    await update.message.reply_text(
        text=build_member_filters_text(_get_member_filters(context)),
        reply_markup=build_member_filters_keyboard(),
        parse_mode="Markdown",
    )
    return True

def build_member_filters_keyboard():
    rows = []
    for i in range(0, len(MEMBER_FILTERS), 2):
        rows.append([
            InlineKeyboardButton(label, callback_data=f"search:filter:member:{key}")
            for key, label in MEMBER_FILTERS[i:i + 2]
        ])
    rows.append([
        InlineKeyboardButton("🔎 Rechercher", callback_data="search:run:member"),
        InlineKeyboardButton("🧹 Réinitialiser", callback_data="search:reset:member"),
    ])
    rows.append([InlineKeyboardButton("⬅️ Retour", callback_data="search:home")])
    return InlineKeyboardMarkup(rows)


def build_member_filters_text(filters=None):
    filters = filters or {}
    lines = [
    "🔎 *RECHERCHE ADHÉRENT*",
    "*Recherche — Adhérents*",
    "",
    "Sélectionnez les critères à renseigner :",
    "",
            ]
    for key, label in MEMBER_FILTERS:
        value = filters.get(key)
        lines.append(f"• {label} : {value if value not in (None, '') else '—'}")
    return "\n".join(lines)


async def recherche_member_filters(update, context):
    query = update.callback_query
    await query.answer()
    filters = _get_member_filters(context)
    await query.edit_message_text(
        text=build_member_filters_text(filters),
        reply_markup=build_member_filters_keyboard(),
        parse_mode="Markdown",
    )


async def search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""
    if data == "search:type:members":
        return await recherche_member_filters(update, context)
    if data == "search:home":
        await query.answer()
        stats = _get_search_stats()
        await query.edit_message_text(
            text=_build_search_text(stats),
            reply_markup=_build_keyboard(stats),
            parse_mode="Markdown",
        )
        return
    if data == "search:close":
        await query.answer()
        await query.edit_message_text(text="🔎 Recherche fermée.")
        return
    if data.startswith("search:filter:member:"):
        key = data.rsplit(":", 1)[-1]
        if key in INTERACTIVE_MEMBER_FILTERS:
            return await prompt_member_filter(update, context, key)
        await query.answer("Ce filtre sera ajouté dans une prochaine étape.", show_alert=True)
        return
    if data == "search:reset:member":
        context.user_data[FILTERS_DATA_KEY] = {}
        context.user_data.pop(PENDING_FILTER_KEY, None)
        await query.answer()
        return await recherche_member_filters(update, context)
    if data == "search:run:member":
        await query.answer()
        await query.edit_message_text(
            text="🔎 *Résultats Adhérents*\n\nAucun résultat exécuté pour le moment.",
            parse_mode="Markdown",
        )


async def recherche_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = AuthManager().get_user(user_id)
    if not user or user[2] not in {"super_admin", "president", "tresorier"}:
        await update.message.reply_text("⛔ Accès refusé à la recherche.")
        return
    stats = _get_search_stats()
    await update.message.reply_text(
        text=_build_search_text(stats),
        reply_markup=_build_keyboard(stats),
        parse_mode="Markdown",
    )
