"""Moteur de synchronisation Dolibarr -> DuckDB.

Dolibarr reste la source de vérité. DuckDB sert de miroir de lecture.
Chaque jeu de données peut être synchronisé indépendamment selon sa fréquence.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from core.db import DatabaseManager
from services.dolibarr_api import DolibarrClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SyncResult:
    component: str
    success: bool
    count: int = 0
    message: str = ""


class SyncService:
    """Centralise les synchronisations métier vers le miroir DuckDB."""

    def __init__(self, client=None, db=None):
        self.client = client or DolibarrClient()
        self.db = db or DatabaseManager()
        self._owns_db = db is None

    def close(self):
        if self._owns_db:
            self.db.close()

    def _sync(self, component: str, fetch: Callable, store: Callable) -> SyncResult:
        try:
            ok, data = fetch()
            if not ok:
                return SyncResult(component, False, 0, str(data))
            rows = data if isinstance(data, list) else []
            ok, message = store(rows)
            return SyncResult(component, bool(ok), len(rows) if ok else 0, str(message))
        except Exception as exc:
            logger.exception("Erreur synchronisation %s", component)
            return SyncResult(component, False, 0, str(exc))

    def sync_contacts(self) -> SyncResult:
        return self._sync("contacts", self.client.get_contacts, self.db.sync_contacts)

    def sync_members(self) -> SyncResult:
        return self._sync("members", self.client.get_members, self.db.sync_members)

    def sync_memberships(self) -> SyncResult:
        return self._sync("memberships", self.client.get_memberships, self.db.sync_memberships)

    def sync_contributions(self) -> SyncResult:
        return self._sync("contributions", self.client.get_contributions, self.db.sync_contributions)

    def sync_profile(self, profile: str) -> list[SyncResult]:
        mapping = {
            "contacts_members": (self.sync_contacts, self.sync_members),
            "finance": (self.sync_memberships, self.sync_contributions),
            "full": (
                self.sync_contacts,
                self.sync_members,
                self.sync_memberships,
                self.sync_contributions,
            ),
        }
        if profile not in mapping:
            raise ValueError(f"Profil de synchronisation inconnu : {profile}")
        return [action() for action in mapping[profile]]

    def sync_full(self) -> list[SyncResult]:
        return self.sync_profile("full")

    def health_snapshot(self) -> dict:
        ok, stats = self.db.get_dashboard_stats()
        return {
            "success": bool(ok),
            "stats": stats if ok else {},
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
