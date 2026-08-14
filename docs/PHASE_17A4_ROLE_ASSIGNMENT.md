# Phase 17A.4 — Attribution des rôles métier

## Objectif

Permettre au Super Admin Telegram de nommer un utilisateur Dolibarr dans
un groupe métier Yessal en utilisant exclusivement son **ID utilisateur
Dolibarr**.

Dolibarr reste la source de vérité. DuckDB est uniquement le miroir local.

## Commandes

Depuis le compte Super Admin :

```text
/nommer_president <ID_DOLIBARR>
/nommer_bureau <ID_DOLIBARR>
/nommer_tresorier <ID_DOLIBARR>
/nommer_admin <ID_DOLIBARR>
/nommer_membre <ID_DOLIBARR>
```

Exemple :

```text
/nommer_tresorier 6
```

## Sécurité

1. La commande exige le rôle `super_admin`.
2. L'argument doit être un identifiant numérique.
3. L'utilisateur doit exister dans Dolibarr.
4. L'utilisateur doit être actif.
5. Le groupe métier doit exister.
6. L'opération est effectuée dans Dolibarr via REST.
7. Le bot resynchronise immédiatement le miroir DuckDB.
8. Les menus Telegram des comptes déjà liés au même utilisateur Dolibarr
   sont rafraîchis.

Un login comme `webmaster` n'est pas accepté par les commandes de
nomination.

## Principe multi-rôles

La nomination **ajoute** l'utilisateur au groupe métier demandé.
Elle ne retire pas ses autres groupes métier.

C'est volontaire : un même utilisateur peut être, par exemple,
`YESSAL_BUREAU` et `YESSAL_TRESORIER`.

La priorité des rôles reste gérée par `core/permissions.py`.

## Utilisateur Telegram non utilisateur Dolibarr

Un compte Telegram non lié à un utilisateur Dolibarr ne peut pas hériter
des rôles métier. Il reste `user` et ne reçoit pas les commandes
réservées au Bureau, Trésorier, Président ou administration.

## Hors périmètre 17A.4

La révocation d'un rôle n'est pas ajoutée dans cette phase, car
l'endpoint Dolibarr de retrait d'une appartenance groupe impose des
droits API supplémentaires. Elle sera traitée séparément après
validation du workflow d'attribution.
