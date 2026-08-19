from datetime import datetime, timezone
from unittest.mock import patch

from modules.search import (
    _member_display_name,
    _member_result_line,
    _build_member_results_text,
    _build_member_results_keyboard,
)


def test_member_name_is_firstname_then_lastname():
    member = {"firstname": "MARIE", "lastname": "DIOP"}
    assert _member_display_name(member) == "MARIE DIOP"


def test_member_result_has_one_field_per_line_and_hides_empty_values():
    member = {
        "firstname": "MARIE",
        "lastname": "DIOP",
        "ref": "A2604-0005",
        "phone": "777621193",
        "address": "",
        "town": None,
        "array_options": {},
    }
    text = _member_result_line(member, 1)
    assert "1. MARIE DIOP" in text
    assert "🪪 Référence : A2604-0005" in text
    assert "📱 Téléphone : 777621193" in text
    assert "📍 Adresse" not in text
    assert "🏙️ Ville" not in text
    assert "  |  " not in text


def test_membership_date_displays_duration():
    start = int(datetime(2025, 5, 21, tzinfo=timezone.utc).timestamp())
    with patch("modules.search.datetime") as mocked_datetime:
        mocked_datetime.now.return_value = datetime(2026, 11, 21, tzinfo=timezone.utc)
        mocked_datetime.fromtimestamp.side_effect = lambda value, tz=None: datetime.fromtimestamp(value, tz=tz)
        text = _member_result_line(
            {"firstname": "MARIE", "lastname": "DIOP", "first_subscription_date": start},
            1,
        )
    assert "21/05/2025 (membre depuis 1 an 6 mois)" in text


def test_results_use_sixty_dash_separator():
    text = _build_member_results_text([
        {"firstname": "MARIE", "lastname": "DIOP"},
        {"firstname": "PAPE", "lastname": "SAMB"},
    ])
    assert "-" * 60 in text


def test_detail_button_contains_index_and_display_name():
    markup = _build_member_results_keyboard([
        {"id": "1", "firstname": "MARIE", "lastname": "DIOP"}
    ])
    labels = [button.text for row in markup.inline_keyboard for button in row]
    assert "👁️ Voir en détails (1 - MARIE DIOP)" in labels
