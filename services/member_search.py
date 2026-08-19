from services.dolibarr_api import DolibarrClient


SEARCHABLE_MEMBER_FIELDS = {
    "lastname": ("lastname",),
    "firstname": ("firstname",),
    "ref": ("ref",),
    "phone": ("phone", "phone_perso", "phone_mobile"),
    "phone_mobile": ("phone_mobile", "phone", "phone_perso"),
}


def _normalize(value):
    return str(value or "").casefold().strip()


def _member_matches(member, filters):
    for key, wanted in (filters or {}).items():
        if not wanted:
            continue
        fields = SEARCHABLE_MEMBER_FIELDS.get(key)
        if not fields:
            continue
        needle = _normalize(wanted)
        if not any(needle in _normalize(member.get(field)) for field in fields):
            return False
    return True


def search_members(filters, limit=1000):
    client = DolibarrClient()
    success, data = client.get_members(limit=limit)
    if not success:
        return False, data
    members = data if isinstance(data, list) else []
    return True, [member for member in members if _member_matches(member, filters)]
