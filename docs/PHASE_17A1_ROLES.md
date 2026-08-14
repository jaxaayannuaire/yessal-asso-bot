# Phase 17A.1-r2 — Séparation groupes techniques / groupes métier

## Décision d'architecture

Le compte Dolibarr `ys-bot` (ID 8 dans l'installation actuelle) utilise le groupe
`Yessal Asso Bot` pour ses permissions techniques/API. Ce groupe est préexistant et
ne doit jamais être interprété comme un rôle humain Telegram.

### Groupes techniques

- `Yessal Asso Bot` : permissions du compte de service/API.

### Groupes métier Yessal

- `YESSAL_SUPER_ADMIN`
- `YESSAL_PRESIDENT`
- `YESSAL_BUREAU`
- `YESSAL_TRESORIER`
- `YESSAL_ADMIN`
- `YESSAL_MEMBRE`

Seuls les groupes métier `YESSAL_*` alimentent le moteur de permissions Telegram.

## Identification

Le lien Telegram ↔ Dolibarr utilise exclusivement `dolibarr_user_id`.

Exemples :

`/lier_moi 7`
`/nommer_tresorier 6`

Les logins comme `webmaster` ou `marie` ne sont pas des identifiants de sécurité.

## Sécurité

La synchronisation conserve le type de groupe (`technical`, `business`, `other`).
Les commandes de création de groupes ne touchent jamais aux groupes techniques.
