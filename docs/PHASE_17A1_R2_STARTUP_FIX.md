# Phase 17A.1-r2 — correctif démarrage

## Incident

Le VPS ne démarrait pas après le déploiement du correctif de synchronisation :

`ImportError: cannot import name 'refresh_command_menu' from 'modules.roles'`

`main.py` importe cette fonction pour construire le menu Telegram dynamique.

## Correctif

`modules/roles.py` réintroduit `refresh_command_menu()` avec :

- commandes communes ;
- commandes membres ;
- commandes rapports/synchronisation ;
- commandes caisse selon `caisse.view` / `caisse.create` ;
- commandes d'administration selon `roles.manage`.

Aucune modification de la logique Dolibarr technique/métier n'est introduite dans ce correctif.
