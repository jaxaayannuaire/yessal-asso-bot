# Phase 17A — Utilisateurs, groupes et permissions Dolibarr

## Principe

Dolibarr est la source de vérité pour les rôles du bot.

Le bot ne considère plus `bot_users.role` comme la source métier principale. Cette colonne reste conservée pour la compatibilité et le bootstrap.

## Groupes standards

- `SUPER_ADMIN`
- `PRESIDENT`
- `BUREAU`
- `TRESORIER`
- `ADMIN`
- `MEMBRE`

Les noms sont normalisés et quelques variantes accentuées sont reconnues.

## Synchronisation

`/sync_roles` récupère depuis l'API REST Dolibarr :

- utilisateurs ;
- groupes ;
- groupes de chaque utilisateur.

DuckDB conserve uniquement le miroir technique : `dolibarr_users`, `dolibarr_groups`, `dolibarr_user_groups`.

## Bootstrap

Le Super Admin peut utiliser :

- `/creer_groupes` — crée les groupes standards s'ils n'existent pas ;
- `/sync_roles` — synchronise Dolibarr → DuckDB ;
- `/lier_moi <login_ou_id>` — lie son Telegram à un utilisateur Dolibarr.

## Nomination

Le Super Admin peut donner un rôle en ajoutant l'utilisateur au groupe Dolibarr correspondant :

- `/nommer_tresorier <login_ou_id>`
- `/nommer_president <login_ou_id>`
- `/nommer_bureau <login_ou_id>`
- `/nommer_admin <login_ou_id>`
- `/nommer_membre <login_ou_id>`

Après chaque nomination, une synchronisation est effectuée.

## Menu Telegram

Le `/start` actualise le menu des commandes pour le chat courant avec `BotCommandScopeChat`. Les commandes administratives ne sont donc pas proposées aux utilisateurs ordinaires.

La sécurité ne dépend cependant jamais uniquement du menu : chaque handler vérifie aussi les droits.

## API Dolibarr

La documentation Dolibarr indique les endpoints utilisateurs/groupes, notamment `GET /users`, `GET /users/groups`, `GET /users/{id}/groups` et l'ajout à un groupe via `GET /users/{id}/setGroup/{group}`. Les opérations d'administration dépendent des permissions de la clé API utilisée par le bot.
