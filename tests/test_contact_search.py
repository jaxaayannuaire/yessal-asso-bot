from modules.search import (
    _contact_display_name,
    _contact_result_line,
    _build_contact_results_text,
    build_contact_filters_text,
)
from services.contact_search import _matches, get_all_contacts
from unittest.mock import patch


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


class _PagedContactsClient:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get_contacts(self, limit=100, page=None):
        self.calls.append((limit, page))
        return True, self.pages.get(page, [])


def test_get_all_contacts_reads_more_than_one_page():
    pages = {
        0: [{"id": index} for index in range(100)],
        1: [{"id": 100 + index} for index in range(20)],
    }
    client = _PagedContactsClient(pages)

    with patch("services.contact_search.DolibarrClient", return_value=client):
        success, contacts = get_all_contacts(page_size=100)

    assert success is True
    assert len(contacts) == 120
    assert client.calls == [(100, 0), (100, 1)]


def test_get_all_contacts_returns_api_error():
    class ErrorClient:
        def get_contacts(self, limit=100, page=None):
            return False, "Erreur API"

    with patch("services.contact_search.DolibarrClient", return_value=ErrorClient()):
        success, result = get_all_contacts()

    assert success is False
    assert result == "Erreur API"
