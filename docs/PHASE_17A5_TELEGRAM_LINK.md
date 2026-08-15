# Phase 17A.5 — Liaison sécurisée Telegram ↔ Dolibarr

## Principe
Dolibarr reste la source de vérité. DuckDB ne conserve que la liaison technique et les jetons.

## Workflow
Super Admin :
`/generer_lien <ID_DOLIBARR>`

Utilisateur :
`/lier <JETON>`

Le jeton est aléatoire, à usage unique, valable 10 minutes et seul son SHA-256 est stocké.

## Règles
- un Telegram actif → un seul utilisateur Dolibarr ;
- un utilisateur Dolibarr actif → un seul Telegram principal ;
- utilisateur Dolibarr obligatoire et actif ;
- `/lier_moi <ID>` ne doit plus faire de liaison directe ;
- bootstrap Super Admin reste l'exception contrôlée par `TELEGRAM_ADMIN_IDS`.

## Super Admin
`YESSAL_SUPER_ADMIN` possède `*`. Le menu doit donc exposer toutes les commandes fonctionnelles du bot.

## Validation
1. Générer un lien pour Marie ID 6.
2. Utiliser le jeton depuis son Telegram.
3. Vérifier `bot_users`.
4. Vérifier que `YESSAL_TRESORIER` reste calculé depuis Dolibarr.
5. Vérifier `/caisse`.
6. Vérifier qu'un second usage du jeton est refusé.
7. Vérifier qu'un Telegram ou Dolibarr déjà lié est refusé.
