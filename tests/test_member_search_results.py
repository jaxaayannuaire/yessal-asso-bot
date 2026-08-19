from modules.search import _build_member_results_text


def test_results_text_contains_member():
    text = _build_member_results_text([
        {"id": 1, "lastname": "SAMB", "firstname": "Pape", "ref": "A1", "phone": "770000000"}
    ])
    assert "Pape SAMB" in text
