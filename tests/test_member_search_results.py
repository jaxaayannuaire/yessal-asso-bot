from modules.search import _build_member_results_text
from services.member_search import _member_matches


def test_member_matches_lastname():
    member = {"lastname": "SAMB", "firstname": "Pape"}
    assert _member_matches(member, {"lastname": "samb"})
    assert not _member_matches(member, {"lastname": "diop"})


def test_member_matches_phone_mobile():
    member = {"phone_mobile": "776328417"}
    assert _member_matches(member, {"phone": "632"})
    assert _member_matches(member, {"phone_mobile": "8417"})


def test_results_text_contains_member():
    text = _build_member_results_text([
        {"id": 1, "lastname": "SAMB", "firstname": "Pape", "ref": "A1", "phone": "770000000"}
    ])
    assert "SAMB Pape" in text
    assert "A1" in text


def test_empty_results_text():
    assert "Aucun adhérent" in _build_member_results_text([])
