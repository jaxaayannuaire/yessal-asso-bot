# Phase 17A.3 — Dolibarr API Groups CRUD

Complète `DolibarrClient` pour Dolibarr 23.x.

## Ajouts

- détection de version via `/status`;
- détection non destructive des capacités API;
- `_put()` et `_delete()`;
- `update_dolibarr_group()`;
- `delete_dolibarr_group()`;
- tests des routes CRUD et des capacités 22.x/23.x.

Dolibarr 23.x expose `POST /groups`, `PUT /groups/{group}` et
`DELETE /groups/{group}` dans son API Users.

Le bot continue à utiliser l'API REST de Dolibarr; aucun SQL direct vers
la base Dolibarr n'est introduit.
