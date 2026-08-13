# Architecture — Yessal Asso Bot

## Principe directeur

Dolibarr est la **source de vérité métier absolue**. Yessal Asso Bot utilise DuckDB comme miroir local, cache de consultation et support des automatisations.

```text
Dolibarr (source de vérité)
        │
        ├── REST API ──> services/dolibarr_api.py
        │                         │
        │                         ▼
        │                    core/db.py
        │                         │
        │                         ▼
        │                      DuckDB
        │                         │
        ▼                         ▼
  Métier ERP              Telegram / Jobs
```

## Couches

- `core/` : infrastructure transverse, accès DuckDB et autorisation.
- `services/` : connecteurs externes, notamment Dolibarr.
- `modules/` : commandes Telegram et automatisations métier.
- `main.py` : assemblage de l'application et enregistrement des handlers/jobs.
- `tests/` : tests ciblés des composants critiques.
- `docs/` : documentation technique et d'exploitation.

## Règles de développement

1. Ne pas faire de DuckDB une nouvelle source de vérité.
2. Les écritures métier futures doivent passer par Dolibarr lorsque le module/API le permet.
3. Les erreurs d'API et de base doivent être journalisées avec `logger.exception()` lorsqu'une trace complète est utile.
4. Les permissions Telegram doivent être centralisées dans `AuthManager`.
5. Les opérations financières devront être idempotentes avant l'intégration Wave.
6. Une évolution doit rester compatible avec le MVP existant ou fournir une migration explicite.
