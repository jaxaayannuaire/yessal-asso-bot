# Changelog — Yessal Asso Bot

## Phase 16.5 — Consolidation technique

### Améliorations

- Nettoyage de `main.py` et centralisation de la construction de l'application.
- Centralisation des rôles et contrôles d'accès dans `core/auth.py`.
- Nettoyage de `core/db.py` : suppression des méthodes dupliquées et transactions de synchronisation.
- Migration DuckDB additive pour les installations ayant un ancien schéma.
- Nettoyage du client REST Dolibarr et gestion homogène des erreurs réseau/JSON.
- Journalisation plus exploitable des jobs et erreurs.
- Ajout d'un `.gitignore` adapté au bot.
- Ajout de documentation technique et de déploiement.

### Compatibilité

Aucune migration destructive n'est prévue par cette phase. Les colonnes historiques DuckDB sont conservées lorsqu'elles existent.
