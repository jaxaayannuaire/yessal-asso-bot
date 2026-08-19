"""Generic multi-selection state engine for Yessal Bot Engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional


@dataclass
class MultiSelectState:
    selected_ids: set[Any] = field(default_factory=set)
    page: int = 1
    query: str = ""


class MultiSelectWizard:
    """Framework-agnostic selection engine; Telegram integration can consume its state."""

    def __init__(
        self,
        items_provider: Callable[[str, int, int], Iterable[Any]],
        item_id: Callable[[Any], Any],
        item_label: Callable[[Any], str],
        page_size: int = 10,
        max_selection: Optional[int] = None,
    ):
        if page_size <= 0:
            raise ValueError("page_size doit être supérieur à zéro.")
        if max_selection is not None and max_selection <= 0:
            raise ValueError("max_selection doit être supérieur à zéro.")
        self.items_provider = items_provider
        self.item_id = item_id
        self.item_label = item_label
        self.page_size = page_size
        self.max_selection = max_selection

    def page_items(self, state: MultiSelectState) -> list[Any]:
        return list(self.items_provider(state.query, state.page, self.page_size))

    def toggle(self, state: MultiSelectState, item: Any) -> bool:
        item_id = self.item_id(item)
        if item_id in state.selected_ids:
            state.selected_ids.remove(item_id)
            return False
        if self.max_selection is not None and len(state.selected_ids) >= self.max_selection:
            raise ValueError("Nombre maximum d'éléments sélectionnés atteint.")
        state.selected_ids.add(item_id)
        return True

    def select_page(self, state: MultiSelectState) -> int:
        items = self.page_items(state)
        for item in items:
            item_id = self.item_id(item)
            if item_id in state.selected_ids:
                continue
            if self.max_selection is not None and len(state.selected_ids) >= self.max_selection:
                break
            state.selected_ids.add(item_id)
        return len(state.selected_ids)

    def deselect_page(self, state: MultiSelectState) -> int:
        for item in self.page_items(state):
            state.selected_ids.discard(self.item_id(item))
        return len(state.selected_ids)

    def set_query(self, state: MultiSelectState, query: str) -> None:
        state.query = query.strip()
        state.page = 1

    def previous_page(self, state: MultiSelectState) -> int:
        state.page = max(1, state.page - 1)
        return state.page

    def next_page(self, state: MultiSelectState) -> int:
        state.page += 1
        return state.page

    def can_continue(self, state: MultiSelectState) -> bool:
        return bool(state.selected_ids)

    def selected_count(self, state: MultiSelectState) -> int:
        return len(state.selected_ids)

    def labels(self, state: MultiSelectState) -> list[str]:
        return [self.item_label(item) for item in self.page_items(state)]
