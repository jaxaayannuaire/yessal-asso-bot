"""Generic advanced search engine for Yessal Bot Engine."""
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional

Provider = Callable[[dict[str, Any], int, int], Iterable[dict[str, Any]]]

@dataclass(frozen=True)
class SearchField:
    key: str
    label: str
    field_type: str = "text"

@dataclass(frozen=True)
class SearchDefinition:
    name: str
    label: str
    fields: tuple[SearchField, ...]
    provider: Provider
    page_size: int = 10

@dataclass
class SearchState:
    definition: str
    filters: dict[str, Any] = field(default_factory=dict)
    page: int = 1

class AdvancedSearch:
    def __init__(self, definitions: dict[str, SearchDefinition]):
        self.definitions = definitions

    def start(self, name: str, filters: Optional[dict[str, Any]] = None) -> SearchState:
        definition = self.definitions[name]
        if definition.page_size <= 0:
            raise ValueError("page_size doit être supérieur à 0.")
        return SearchState(name, dict(filters or {}), 1)

    def set_filter(self, state: SearchState, key: str, value: Any) -> None:
        definition = self.definitions[state.definition]
        if key not in {f.key for f in definition.fields}:
            raise KeyError(f"Filtre inconnu : {key}")
        if value in (None, ""):
            state.filters.pop(key, None)
        else:
            state.filters[key] = value
        state.page = 1

    def clear_filters(self, state: SearchState) -> None:
        state.filters.clear()
        state.page = 1

    def results(self, state: SearchState) -> list[dict[str, Any]]:
        d = self.definitions[state.definition]
        return list(d.provider(state.filters, state.page, d.page_size))

    def next_page(self, state: SearchState) -> int:
        state.page += 1
        return state.page

    def previous_page(self, state: SearchState) -> int:
        if state.page > 1:
            state.page -= 1
        return state.page

    def can_previous(self, state: SearchState) -> bool:
        return state.page > 1

def member_search_definition(provider: Provider, page_size: int = 10) -> SearchDefinition:
    if page_size <= 0:
        raise ValueError("page_size doit être supérieur à 0.")
    return SearchDefinition(
        "member", "Adhérent", (
            SearchField("ref", "Référence"), SearchField("lastname", "Nom"),
            SearchField("firstname", "Prénom"), SearchField("phone", "Téléphone"),
            SearchField("phone_perso", "Tél. perso."), SearchField("phone_mobile", "WhatsApp"),
            SearchField("email", "Email"), SearchField("address", "Adresse"),
            SearchField("zip", "Code postal"), SearchField("town", "Ville"),
            SearchField("gender", "Sexe"), SearchField("morphy", "Nature"),
            SearchField("typeid", "Type d’adhérent"), SearchField("adhesion_month", "Mois"),
            SearchField("adhesion_year", "Année"), SearchField("fonction", "Fonction"),
            SearchField("responsabilite", "Responsabilité"), SearchField("tag", "Tag / catégorie"),
        ), provider, page_size)
