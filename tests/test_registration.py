import pytest

import modules.registration as registration


class FakeClient:
    def __init__(self):
        self.calls = []
        self.member_types = [{"id": "1", "label": "Membre actif", "statut": "1"}]

    def get_dolibarr_member_types(self, limit=100):
        self.calls.append(("types", limit))
        return True, self.member_types

    def create_dolibarr_member(self, payload):
        self.calls.append(("member", payload))
        return True, "101"

    def create_dolibarr_contact(self, payload):
        self.calls.append(("contact", payload))
        return True, "202"

    def create_dolibarr_thirdparty(self, payload):
        self.calls.append(("thirdparty", payload))
        return True, "303"

    def create_dolibarr_user(self, payload):
        self.calls.append(("user", payload))
        return True, "404"

    def delete_dolibarr_user(self, user_id):
        self.calls.append(("delete_user", user_id))
        return True, {"success": {"code": 200}}

    def add_user_to_group(self, user_id, group_id):
        self.calls.append(("group", user_id, group_id))
        return True, 1


def test_member_type_is_auto_selected(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(registration, "DolibarrClient", lambda: client)
    ok, value = registration._member_type_id(client)
    assert ok is True
    assert value == 1


def test_member_type_requires_explicit_id_when_multiple(monkeypatch):
    client = FakeClient()
    client.member_types = [
        {"id": "1", "label": "Standard", "statut": "1"},
        {"id": "2", "label": "Jeune", "statut": "1"},
    ]
    ok, message = registration._member_type_id(client)
    assert ok is False
    assert "1=Standard" in message
    assert "2=Jeune" in message


def test_safe_login():
    assert registration._safe_login("Sidy", "Diakhoumpa") == "sidydiakhoumpa"
    assert registration._safe_login("Sidy", "Diakhoumpa", "sdia") == "sdia"


def test_extract_id():
    assert registration._extract_id("123") == "123"
    assert registration._extract_id({"id": 456}) == "456"
    assert registration._extract_id({"success": {"id": "789"}}) == "789"
