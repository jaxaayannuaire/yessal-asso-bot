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


def search_contacts(filters, limit=1000):
    success, data = DolibarrClient().get_contacts(limit=limit)
    if not success:
        return False, data
    if not isinstance(data, list):
        return True, []
    return True, [contact for contact in data if _matches(contact, filters)]
