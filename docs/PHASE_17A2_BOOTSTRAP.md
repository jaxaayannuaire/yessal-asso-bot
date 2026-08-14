# Phase 17A.2 — Bootstrap du Super Admin

## Pourquoi

La base `bot_users` du VPS ne contient actuellement aucun utilisateur. Le mécanisme
de compatibilité de `AuthManager` ne peut donc pas bootstrapper le premier Super Admin.

## Solution

Une commande temporaire et sécurisée :

`/bootstrap_super_admin <ID_DOLIBARR>`

est autorisée uniquement si le Telegram ID de l'expéditeur figure dans
`TELEGRAM_ADMIN_IDS` du `.env`.

Le bootstrap :

1. vérifie qu'aucun Super Admin actif n'existe déjà ;
2. vérifie/synchronise l'utilisateur Dolibarr demandé ;
3. crée `YESSAL_SUPER_ADMIN` si nécessaire ;
4. ajoute l'utilisateur Dolibarr au groupe ;
5. crée le lien Telegram ↔ `dolibarr_user_id` ;
6. resynchronise DuckDB.

L'identifiant Dolibarr reste numérique. Le login (`webmaster`) n'est jamais utilisé
comme identifiant de sécurité.

## Exemple

Si `webmaster` possède l'ID Dolibarr `7` :

`/bootstrap_super_admin 7`

Après réussite, le Super Admin peut utiliser :

`/creer_groupes`

pour créer les cinq autres groupes métier.

## Groupe technique

`Yessal Asso Bot` n'est jamais modifié par ce bootstrap.
