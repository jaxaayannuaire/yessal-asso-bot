"""Présentation uniforme des résultats et détails des contacts."""

from __future__ import annotations

from services.dolibarr_api import DolibarrClient

SEPARATOR = "-" * 60

FIELD_LABELS = {
    "id": "ID", "lastname": "Nom", "firstname": "Prénom", "name": "Nom",
    "societe": "Société / organisation", "company": "Société / organisation",
    "phone": "Téléphone", "phone_pro": "Téléphone",
    "phone_mobile": "WhatsApp", "phone_perso": "WhatsApp",
    "email": "Email", "address": "Adresse", "zip": "Code postal",
    "town": "Ville", "poste": "Fonction",
    "type": "Type de contact", "type_contact": "Type de contact",
    "statut": "Statut",
}

FIELD_ICONS = {
    "type": "👥", "type_contact": "👥", "poste": "💼",
    "phone": "📱", "phone_pro": "📱",
    "phone_mobile": "💬", "phone_perso": "💬",
    "email": "✉️", "address": "📍", "zip": "📮", "town": "🏙️",
    "societe": "🏢", "company": "🏢",
}

SUMMARY_FIELDS = (
    "type", "type_contact", "poste",
    "phone_mobile", "phone_perso", "phone", "phone_pro",
    "email", "town", "societe", "company", "address", "zip",
)

METADATA_FIELDS = {
    "array_options", "id", "entity", "rowid", "status", "statut",
    "date_creation", "date_modification", "user_creation_id",
    "user_modification_id", "canvas",
}

DETAIL_EXCLUDED_FIELDS = {
    "id", "firstname", "lastname", "name", "ref", "reference",
    "array_options",
}


def _has_value(value):
    return value not in (None, "", "—", [], {}, 0, "0")


def _display_name(contact):
    firstname = str(contact.get("firstname") or "").strip()
    lastname = str(contact.get("lastname") or "").strip()
    return (
        f"{firstname} {lastname}".strip()
        or contact.get("name")
        or contact.get("societe")
        or "Sans nom"
    )


def _format_field(key, value):
    label = FIELD_LABELS.get(
        key,
        key.replace("options_", "").replace("_", " ").strip().capitalize(),
    )
    icon = FIELD_ICONS.get(key, "")
    prefix = f"{icon} " if icon else ""
    return f"{prefix}{label} : {value}"


def _summary_values(contact):
    seen = set()

    for key in SUMMARY_FIELDS:
        value = contact.get(key)

        if key == "type_contact" and not _has_value(value):
            value = contact.get("type")
        if key == "phone_perso" and not _has_value(value):
            value = contact.get("phone_mobile")
        if key == "phone_pro" and not _has_value(value):
            value = contact.get("phone")
        if key == "company" and not _has_value(value):
            value = contact.get("societe")

        if not _has_value(value):
            continue

        label = FIELD_LABELS.get(key, key)
        if label in seen:
            continue

        seen.add(label)
        yield key, value


def contact_summary_line(contact, index):
    contact_id = contact.get("id")
    suffix = f" (ID : {contact_id})" if _has_value(contact_id) else ""

    lines = [f"*{index}. {_display_name(contact)}*{suffix}"]

    for key, value in _summary_values(contact):
        lines.append(_format_field(key, value))
        if len(lines) >= 5:
            break

    return "\n".join(lines)


def build_contact_results_text(results):
    if not results:
        return (
            "📇 *RÉSULTATS CONTACTS*\n\n"
            "Aucun contact ne correspond aux critères."
        )

    lines = [
        "📇 *RÉSULTATS CONTACTS*",
        f"👥 {len(results)} résultat(s)",
        "",
    ]

    for index, contact in enumerate(results, start=1):
        if index > 1:
            lines.append(SEPARATOR)
        lines.append(contact_summary_line(contact, index))

    return "\n".join(lines)


def _iter_detail_fields(contact):
    seen_labels = set()

    ordered = (
        "type", "type_contact", "poste", "societe", "company",
        "phone", "phone_pro", "phone_mobile", "phone_perso", "email",
        "address", "zip", "town",
    )

    for key in ordered:
        value = contact.get(key)

        if not _has_value(value):
            continue

        label = FIELD_LABELS.get(key, key)
        if label in seen_labels:
            continue

        seen_labels.add(label)
        yield key, value

    for key, value in contact.items():
        if (
            key in DETAIL_EXCLUDED_FIELDS
            or key in METADATA_FIELDS
            or key in ordered
            or not _has_value(value)
        ):
            continue

        if isinstance(value, (dict, list, tuple)):
            continue

        label = FIELD_LABELS.get(
            key,
            key.replace("_", " ").capitalize(),
        )

        if label in seen_labels:
            continue

        seen_labels.add(label)
        yield key, value

    options = contact.get("array_options") or {}

    if isinstance(options, dict):
        for key, value in options.items():
            if not _has_value(value):
                continue

            clean_key = str(key).replace("options_", "", 1)
            label = FIELD_LABELS.get(
                clean_key,
                clean_key.replace("_", " ").capitalize(),
            )

            if label in seen_labels:
                continue

            seen_labels.add(label)
            yield clean_key, value


def build_contact_detail_text(contact):
    contact_id = contact.get("id")
    suffix = f" (ID : {contact_id})" if _has_value(contact_id) else ""

    lines = [
        "📇 *DÉTAIL CONTACT*",
        "",
        f"*{_display_name(contact)}*{suffix}",
    ]

    for key, value in _iter_detail_fields(contact):
        lines.append(_format_field(key, value))

    return "\n".join(lines)


def get_contact_details(contact_id, fallback=None):
    success, data = DolibarrClient()._get(f"contacts/{int(contact_id)}")

    if success and isinstance(data, dict):
        return True, data

    return False, fallback or data


def install_search_presentation():
    import modules.search as search

    search._contact_result_line = contact_summary_line
    search._build_contact_results_text = build_contact_results_text
