import pytest

import modules.telegram_link as telegram_link
from core.db import DatabaseManager


class FakeDolibarrClient:
    USERS = {
        "6": {"id": "6", "login": "marie", "firstname": "Marie",
              "lastname": "Diop", "statut": "1"},
        "9": {"id": "9", "login": "inactive", "firstname": "Inactive",
              "lastname": "User", "statut": "0"},
    }

    def get_dolibarr_user(self, user_id):
        user = self.USERS.get(str(user_id))
        return (True, user) if user else (False, "Utilisateur introuvable")


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "test.duckdb"))
    database = DatabaseManager()
    database.init_db()
    yield database
    database.close()


def test_pairing_token_is_hashed(db):
    raw, _ = telegram_link.create_pairing_token(db, "6", "7532614749")
    digest = telegram_link._hash_token(raw)
    stored = db.connect().execute(
        "SELECT token_hash FROM telegram_link_tokens"
    ).fetchone()[0]
    assert stored == digest
    assert stored != raw


def test_pairing_ttl(db):
    _, expires_at = telegram_link.create_pairing_token(db, "6", "7532614749")
    stored = db.connect().execute(
        "SELECT expires_at FROM telegram_link_tokens"
    ).fetchone()[0]
    assert stored == expires_at


def test_consume_valid_token_uses_dolibarr_api(db, monkeypatch):
    monkeypatch.setattr(telegram_link, "DolibarrClient", FakeDolibarrClient)
    raw, _ = telegram_link.create_pairing_token(db, "6", "7532614749")
    ok, result = telegram_link.consume_pairing_token(
        db, raw, "111111", "marie"
    )
    assert ok is True
    assert result["dolibarr_user_id"] == "6"
    row = db.connect().execute(
        "SELECT telegram_id,dolibarr_user_id,role FROM bot_users "
        "WHERE telegram_id='111111'"
    ).fetchone()
    assert row == ("111111", "6", "user")


def test_expired_token_rejected(db, monkeypatch):
    monkeypatch.setattr(telegram_link, "DolibarrClient", FakeDolibarrClient)
    raw, _ = telegram_link.create_pairing_token(
        db, "6", "7532614749", ttl_minutes=-1
    )
    ok, message = telegram_link.consume_pairing_token(
        db, raw, "111111", "marie"
    )
    assert ok is False
    assert "expiré" in message


def test_used_token_rejected(db, monkeypatch):
    monkeypatch.setattr(telegram_link, "DolibarrClient", FakeDolibarrClient)
    raw, _ = telegram_link.create_pairing_token(db, "6", "7532614749")
    assert telegram_link.consume_pairing_token(
        db, raw, "111111", "marie"
    )[0] is True
    ok, message = telegram_link.consume_pairing_token(
        db, raw, "222222", "other"
    )
    assert ok is False
    assert "déjà été utilisé" in message


def test_telegram_already_linked_to_other_dolibarr_rejected(db, monkeypatch):
    monkeypatch.setattr(telegram_link, "DolibarrClient", FakeDolibarrClient)
    db.connect().execute(
        "INSERT INTO bot_users "
        "(telegram_id,username,role,is_active,dolibarr_user_id) "
        "VALUES ('111111','old','user',TRUE,'9')"
    )
    raw, _ = telegram_link.create_pairing_token(db, "6", "7532614749")
    ok, message = telegram_link.consume_pairing_token(
        db, raw, "111111", "marie"
    )
    assert ok is False
    assert "déjà lié à un autre utilisateur" in message


def test_dolibarr_user_already_linked_rejected(db, monkeypatch):
    monkeypatch.setattr(telegram_link, "DolibarrClient", FakeDolibarrClient)
    db.connect().execute(
        "INSERT INTO bot_users "
        "(telegram_id,username,role,is_active,dolibarr_user_id) "
        "VALUES ('999999','other','user',TRUE,'6')"
    )
    raw, _ = telegram_link.create_pairing_token(db, "6", "7532614749")
    ok, message = telegram_link.consume_pairing_token(
        db, raw, "111111", "marie"
    )
    assert ok is False
    assert "possède déjà un compte Telegram" in message


def test_inactive_dolibarr_user_rejected(db, monkeypatch):
    monkeypatch.setattr(telegram_link, "DolibarrClient", FakeDolibarrClient)
    raw, _ = telegram_link.create_pairing_token(db, "9", "7532614749")
    ok, message = telegram_link.consume_pairing_token(
        db, raw, "111111", "inactive"
    )
    assert ok is False
    assert "désactivé" in message
