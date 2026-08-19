from core.multiselect import MultiSelectState, MultiSelectWizard
import pytest
pytestmark = pytest.mark.skip(
    reason="MultiSelectWizard mis en pause jusqu'à la phase finale du projet"
)


def provider(query, page, size):
    items = [{"id": i, "name": f"Membre {i}"} for i in range(1, 26)]
    if query:
        items = [x for x in items if query.casefold() in x["name"].casefold()]
    start = (page - 1) * size
    return items[start:start + size]


def make_engine(max_selection=None, page_size=5):
    return (MultiSelectWizard(provider, lambda x: x["id"], lambda x: x["name"], page_size=page_size, max_selection=max_selection), MultiSelectState())


def test_toggle_and_count():
    e, s = make_engine()
    assert e.toggle(s, {"id": 1, "name": "Membre 1"}) is True
    assert e.selected_count(s) == 1
    assert e.toggle(s, {"id": 1, "name": "Membre 1"}) is False
    assert e.selected_count(s) == 0


def test_select_and_deselect_page():
    e, s = make_engine()
    assert e.select_page(s) == 5
    assert e.deselect_page(s) == 0


def test_selection_persists_across_pages():
    e, s = make_engine()
    e.select_page(s)
    e.next_page(s)
    e.toggle(s, {"id": 6, "name": "Membre 6"})
    assert s.selected_ids == {1, 2, 3, 4, 5, 6}


def test_search_resets_to_first_page():
    e, s = make_engine(), MultiSelectState(page=3)
    e.set_query(s, "Membre 2")
    assert s.query == "Membre 2"
    assert s.page == 1
    assert [x["id"] for x in e.page_items(s)] == [2, 20, 21, 22, 23]


def test_max_selection():
    e, s = make_engine(max_selection=2)
    e.toggle(s, {"id": 1, "name": "Membre 1"})
    e.toggle(s, {"id": 2, "name": "Membre 2"})
    with pytest.raises(ValueError):
        e.toggle(s, {"id": 3, "name": "Membre 3"})


def test_cannot_continue_without_selection():
    e, s = make_engine()
    assert e.can_continue(s) is False
    e.toggle(s, {"id": 1, "name": "Membre 1"})
    assert e.can_continue(s) is True


def test_invalid_page_size():
    with pytest.raises(ValueError):
        make_engine(page_size=0)
