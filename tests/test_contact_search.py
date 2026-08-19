from modules.search import (
    _contact_display_name,
    _contact_result_line,
    _build_contact_results_text,
    build_contact_filters_text,
)
from services.contact_search import _matches


def test_contact_name_is_firstname_then_lastname():
    assert _contact_display_name({"firstname": "MARIE", "lastname": "DIOP"}) == "MARIE DIOP"


def test_contact_result_hides_empty_fields():
    text = _contact_result_line(
        {
            "firstname": "MARIE",
            "lastname": "DIOP",
            "phone": "770000000",
            "email": "",
            "town": None,
        },
        1,
    )
    assert "1. MARIE DIOP" in text
    assert "Téléphone : 770000000" in text
    assert "Email" not in text
    assert "Ville" not in text


def test_contact_results_use_sixty_dash_separator():
    text = _build_contact_results_text([
        {"firstname": "MARIE", "lastname": "DIOP"},
        {"firstname": "PAPE", "lastname": "SAMB"},
    ])
    assert "-" * 60 in text


def test_contact_filters_show_selected_value_in_bold():
    text = build_contact_filters_text({"lastname": "Diop"})
    assert "Nom : *Diop*" in text


def test_contact_search_matching_is_case_insensitive():
    contact = {"firstname": "Marie", "lastname": "DIOP", "town": "Dakar"}
    assert _matches(contact, {"lastname": "diop", "town": "DAK"})
    assert not _matches(contact, {"lastname": "fall"})
