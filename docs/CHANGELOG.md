# Changelog

## Phase 17 — Caisse & Trésorerie

- Ajout du module `modules/cash.py`.
- Ajout de `/caisse`, `/entree` et `/sortie`.
- Ajout du workflow de confirmation Telegram.
- Ajout de la validation Président/Super Admin pour les dépenses du trésorier au-dessus du seuil configuré.
- Ajout de l'idempotence et de l'audit local des opérations financières.
- Ajout des appels Dolibarr `bankaccounts`, `balance` et `lines`.
- Ajout des tests DuckDB du workflow technique.
