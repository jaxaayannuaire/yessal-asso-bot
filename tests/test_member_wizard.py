import pytest

from modules.member_wizard import _email, _phone, _date, _summary, DEFAULT_MEMBER_MORPHY


def test_email_x_uses_default():
    assert _email("X") == "email@email.com"


def test_phone_is_required_and_normalized():
    assert _phone("+221 770000004") == "770000004"


def test_invalid_phone_rejected():
    with pytest.raises(ValueError):
        _phone("123")


def test_date_parser():
    assert _date("16/08/2026") == "2026-08-16"


def test_date_parser_rejects_impossible_date():
    with pytest.raises(ValueError):
        _date("31/02/2026")


def test_default_morphy_is_physical_person():
    assert DEFAULT_MEMBER_MORPHY == "phy"


def test_summary_contains_address_town_and_morphy():
    summary = _summary({
        "lastname": "Diop",
        "firstname": "Mandiaye",
        "sex": "H",
        "morphy": "phy",
        "phone": "786568890",
        "email": "a@example.com",
        "address": "Dakar Plateau",
        "town": "Dakar",
        "type_id": "1",
        "date_adhesion": "2026-08-18",
    })
    assert "Personne physique" in summary
    assert "Dakar Plateau" in summary
    assert "Dakar" in summary


def test_summary_escapes_html_values():
    summary = _summary({
        "lastname": "<script>alert(1)</script>",
        "firstname": "Jean & Paul",
        "sex": "H",
        "morphy": "phy",
        "phone": "770000004",
        "email": "a@example.com",
        "address": "Rue <1>",
        "town": "Dakar",
        "type_id": "1",
        "date_adhesion": "2026-08-18",
    })
    assert "<script>" not in summary
    assert "&lt;script&gt;" in summary
    assert "Jean &amp; Paul" in summary
