import pytest
from core.search import AdvancedSearch, SearchState, member_search_definition

def provider(filters, page, size):
    items = [{"id": i, "lastname": "Diop" if i <= 2 else "Fall"} for i in range(1, 16)]
    if filters.get("lastname"):
        q = str(filters["lastname"]).casefold()
        items = [x for x in items if q in x["lastname"].casefold()]
    return items[(page-1)*size:page*size]

def make_search(page_size=5):
    return AdvancedSearch({"member": member_search_definition(provider, page_size)})

def test_start_creates_state():
    s=make_search().start("member"); assert isinstance(s, SearchState) and s.page == 1

def test_set_filter_resets_page():
    e=make_search(); s=e.start("member"); s.page=3; e.set_filter(s,"lastname","Diop"); assert s.page==1

def test_empty_filter_is_removed():
    e=make_search(); s=e.start("member",{"lastname":"Diop"}); e.set_filter(s,"lastname",""); assert s.filters=={}

def test_unknown_filter_rejected():
    e=make_search(); s=e.start("member")
    with pytest.raises(KeyError): e.set_filter(s,"unknown","x")

def test_results_are_paginated():
    e=make_search(); s=e.start("member"); assert len(e.results(s))==5; e.next_page(s); assert s.page==2

def test_previous_page():
    e=make_search(); s=e.start("member"); assert e.previous_page(s)==1; e.next_page(s); assert e.can_previous(s); assert e.previous_page(s)==1

def test_clear_filters():
    e=make_search(); s=e.start("member",{"lastname":"Diop"}); s.page=2; e.clear_filters(s); assert s.filters=={} and s.page==1

def test_member_fields():
    keys={f.key for f in member_search_definition(provider).fields}
    assert {"ref","lastname","firstname","phone","town","gender","morphy","typeid","adhesion_month","adhesion_year","fonction","responsabilite","tag"} <= keys

def test_invalid_page_size():
    with pytest.raises(ValueError): make_search(page_size=0)
