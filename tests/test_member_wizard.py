import pytest

from modules.member_wizard import _email, _phone, _date, _summary


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


def test_summary_escapes_html_values():
    summary = _summary({
        "lastname": "<script>alert(1)</script>",
        "firstname": "Jean & Paul",
        "sex": "H",
        "phone": "770000004",
        "email": "a@example.com",
        "type_id": "1",
        "date_adhesion": "2026-08-18",
    })
    assert "<script>" not in summary
    assert "&lt;script&gt;" in summary
    assert "Jean &amp; Paul" in summary
