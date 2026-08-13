# Phase 17 — Caisse & Trésorerie

## Objectif

Permettre au trésorier et au bureau de consulter les comptes/caisse Dolibarr et de préparer des entrées/sorties depuis Telegram, tout en conservant Dolibarr comme source de vérité financière.

## Commandes

- `/caisse` : liste les comptes bancaires/caisse et leurs soldes réels Dolibarr.
- `/entree <montant> <compte_id> <libellé>` : prépare une entrée.
- `/sortie <montant> <compte_id> <libellé>` : prépare une sortie.

Exemple :

```text
/entree 5000 1 Cotisation Awa FALL
/sortie 15000 1 Transport réunion
```

## Workflow de sécurité

1. Le bot crée une demande locale `pending_confirmation`.
2. Telegram affiche le récapitulatif et demande une confirmation explicite.
3. Une dépense effectuée par le trésorier et supérieure ou égale au seuil `CASH_PRESIDENT_APPROVAL_THRESHOLD` passe en `pending_approval`.
4. Le Président ou le Super Admin peut approuver ou refuser.
5. Après approbation, le bot écrit la ligne dans Dolibarr.
6. Le résultat Dolibarr est conservé dans l'audit local (`dolibarr_line_id`).

Aucune écriture financière n'est effectuée avant la confirmation/validation requise.

## Source de vérité

Dolibarr fournit :

- la liste des comptes (`bankaccounts`) ;
- les soldes (`bankaccounts/{id}/balance`) ;
- les écritures (`bankaccounts/{id}/lines`).

Le bot ne calcule pas un solde métier parallèle dans DuckDB.

## Idempotence et audit

DuckDB conserve uniquement :

- demandes de caisse ;
- états de workflow ;
- clé d'idempotence ;
- identifiant de ligne Dolibarr ;
- événements d'audit.

La documentation REST officielle de Dolibarr confirme que l'API REST utilise les méthodes GET/POST/PUT/DELETE et le header `DOLAPIKEY`; l'API `bankaccounts` expose notamment les comptes, soldes et lignes d'écriture. urlDocumentation REST Dolibarrhttps://wiki.dolibarr.org/index.php/Module_Web_Services_API_REST_%28developer%29
