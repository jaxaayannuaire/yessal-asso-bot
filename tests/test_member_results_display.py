from modules.search import _member_result_line, _build_member_results_text


def test_member_result_hides_empty_fields():
    text = _member_result_line(
        {
            "lastname": "DIOP",
            "firstname": "Marie",
            "ref": "A2604-0005",
            "phone": "",
            "address": "",
            "town": None,
            "array_options": {},
        },
        1,
    )
    assert "A2604-0005" in text
    assert "📱" not in text
    assert "📍" not in text
    assert "🏙️" not in text
    assert "—" not in text


def test_member_result_keeps_populated_fields():
    text = _member_result_line(
        {
            "lastname": "DIOP",
            "firstname": "Marie",
            "ref": "A2604-0005",
            "phone": "777621193",
            "town": "Dakar",
            "type": "Membre actif",
            "array_options": {
                "options_responsabilite": "Trésorière",
            },
        },
        1,
    )
    assert "777621193" in text
    assert "Dakar" in text
    assert "Membre actif" in text
    assert "Trésorière" in text


def test_results_have_dashed_separator():
    text = _build_member_results_text([
        {"id": "1", "lastname": "DIOP", "firstname": "Marie"},
        {"id": "2", "lastname": "SAMB", "firstname": "Pape"},
    ])
    assert "--------------------" in text
