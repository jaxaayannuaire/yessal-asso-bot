# Phase 17A.1-r2 — correctif de synchronisation DuckDB

Le correctif rend les INSERT de `dolibarr_groups` et `dolibarr_user_groups`
indépendants de l'ordre physique des colonnes DuckDB.

Cela est nécessaire car une base créée par une version antérieure peut avoir
`group_type` ajouté par `ALTER TABLE`, donc placé après `last_sync`.

## Règles

- `Yessal Asso Bot` reste un groupe technique du compte `ys-bot`.
- Les groupes `YESSAL_*` sont les groupes métier.
- Seuls les groupes métier donnent des rôles Telegram.
- Le lien Telegram ↔ Dolibarr utilise exclusivement `dolibarr_user_id`.
- La synchronisation ne modifie que le miroir DuckDB, jamais Dolibarr.

## Important

Le précédent échec de synchronisation n'a pas modifié Dolibarr.
Il a pu vider partiellement le miroir local avant l'erreur ; le prochain
lancement avec ce correctif reconstruira le miroir à partir de Dolibarr.
