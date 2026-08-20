from modules.contact_presentation import (
    SEPARATOR,
    build_contact_detail_text,
    build_contact_results_text,
    contact_summary_line,
)


def test_contact_summary_has_maximum_five_lines_and_id():
    contact = {
        "id": 113,
        "firstname": "Arame",
        "lastname": "DIOP",
        "type": "Bénéficiaire don",
        "poste": "Social",
        "phone_mobile": "769035690",
        "email": "arame@example.com",
        "town": "Dakar",
        "ref": "113",
    }
    text = contact_summary_line(contact, 9)
    lines = text.splitlines()
    assert lines[0] == "*9. Arame DIOP* (ID : 113)"
    assert len(lines) == 5
    assert "👥 Type de contact : Bénéficiaire don" in text
    assert "💼 Fonction : Social" in text
    assert "💬 WhatsApp : 769035690" in text
    assert "✉️ Email : arame@example.com" in text
    assert "Dakar" not in text


def test_contact_results_separator_has_no_blank_lines():
    results = [
        {"id": 1, "firstname": "Awa", "lastname": "DIOP", "poste": "Social"},
        {"id": 2, "firstname": "Fatou", "lastname": "DIOP", "poste": "Finance"},
    ]
    text = build_contact_results_text(results)
    assert "*1. Awa DIOP* (ID : 1)\n💼 Fonction : Social" in text
    assert f"💼 Fonction : Social\n{SEPARATOR}\n*2. Fatou DIOP* (ID : 2)" in text
    assert f"\n\n{SEPARATOR}\n" not in text
    assert f"\n{SEPARATOR}\n\n" not in text


def test_contact_detail_shows_non_empty_standard_and_extrafields():
    contact = {
        "id": 113,
        "firstname": "Arame",
        "lastname": "DIOP",
        "poste": "Social",
        "phone_mobile": "769035690",
        "email": "",
        "town": None,
        "array_options": {
            "options_responsabilite": "Coordination",
            "options_region": "Dakar",
            "options_vide": "",
        },
    }
    text = build_contact_detail_text(contact)
    assert "Arame DIOP* (ID : 113)" in text
    assert "💼 Fonction : Social" in text
    assert "💬 WhatsApp : 769035690" in text
    assert "Responsabilite : Coordination" in text
    assert "Region : Dakar" in text
    assert "Email" not in text
    assert "Ville" not in text
    assert "Vide" not in text
