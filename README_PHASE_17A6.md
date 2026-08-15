# Phase 17A.6 — Inscription associative et opérateurs

Ajouts:
- `/inscrire_membre NOM;PRENOM;TELEPHONE;EMAIL;TYPEID`
- `/creer_contact NOM;PRENOM;TELEPHONE;EMAIL;TIERSID`
- `/creer_tiers NOM;TELEPHONE;EMAIL`
- `/creer_operateur NOM;PRENOM;LOGIN;EMAIL;TELEPHONE;ROLE;TYPEID`

Droits:
- Président, Bureau, Trésorier : membres/contacts/tiers.
- Super Admin : opérateurs + attribution du groupe métier.

Le compte opérateur est créé dans Dolibarr sans mot de passe fourni par Telegram,
puis un jeton 17A.5 à usage unique est généré. L'opérateur utilise `/lier TOKEN`.
