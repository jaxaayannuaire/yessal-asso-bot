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

    def delete_dolibarr_member(self, member_id):
        self.calls.append(("delete_member", member_id))
        return True, {"success": {"code": 200}}

    def link_dolibarr_user_to_member(self, user_id, member_id):
        self.calls.append(("link_member", user_id, member_id))
        return True, {"id": str(user_id), "fk_member": str(member_id)}

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


def test_link_dolibarr_user_to_member():
    client = FakeClient()
    ok, result = client.link_dolibarr_user_to_member("404", "101")
    assert ok is True
    assert result["fk_member"] == "101"
    assert ("link_member", "404", "101") in client.calls


def test_operator_confirmation_uses_html_and_escapes_markdown_sensitive_values():
    confirmation = registration._operator_confirmation_message(
        "Amadou", "TESTOPERATEUR", "amadou2026test2", "12", "16",
        "tresorier", "abc_def-123",
    )

    assert "parse_mode=\"Markdown\"" not in confirmation
    assert "<code>YESSAL_TRESORIER</code>" in confirmation
    assert "<code>abc_def-123</code>" in confirmation
    assert "<code>/lier abc_def-123</code>" in confirmation


def test_operator_confirmation_escapes_html_values():
    confirmation = registration._operator_confirmation_message(
        "Amadou &", "<TEST>", "login_&", "12", "16",
        "tresorier", "tok_<x>",
    )

    assert "Amadou &amp; &lt;TEST&gt;" in confirmation
    assert "<code>login_&amp;</code>" in confirmation
    assert "<code>tok_&lt;x&gt;</code>" in confirmation
