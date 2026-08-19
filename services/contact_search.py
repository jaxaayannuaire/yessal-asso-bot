from services.dolibarr_api import DolibarrClient


SEARCH_FIELDS = (
    "lastname",
    "firstname",
    "societe",
    "phone",
    "phone_mobile",
    "email",
    "address",
    "zip",
    "town",
    "poste",
)


def _normalize(value):
    return str(value or "").casefold().strip()


def _matches(contact, filters):
    for key, expected in (filters or {}).items():
        if key not in SEARCH_FIELDS or expected in (None, ""):
            continue

        actual = contact.get(key)
        if key == "societe":
            actual = actual or contact.get("company")

        if _normalize(expected) not in _normalize(actual):
            return False
    return True


def _contact_list(data):
    """Normalise les différentes formes de réponse possibles de l'API."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "contacts", "results"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    return []


def get_all_contacts(page_size=100, max_pages=1000):
    """Récupère toutes les pages de contacts Dolibarr."""
    client = DolibarrClient()
    contacts = []

    for page in range(max_pages):
        success, data = client.get_contacts(limit=page_size, page=page)
        if not success:
            return False, data

        batch = _contact_list(data)
        contacts.extend(batch)

        if len(batch) < page_size:
            break
    else:
        return False, "Pagination des contacts interrompue après la limite de sécurité."

    return True, contacts


def search_contacts(filters, limit=None):
    """Recherche localement dans tous les contacts récupérés par pagination."""
    page_size = 100
    if limit is not None:
        try:
            page_size = max(1, min(int(limit), 1000))
        except (TypeError, ValueError):
            page_size = 100

    success, data = get_all_contacts(page_size=page_size)
    if not success:
        return False, data

    return True, [contact for contact in data if _matches(contact, filters)]
