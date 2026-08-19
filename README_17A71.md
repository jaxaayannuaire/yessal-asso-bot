# 17A.7.1 — Wizard interactif d'inscription

Cette étape ajoute le parcours conversationnel d'inscription d'un adhérent.

Commande :

/inscrire_membre

Le trésorier répond étape par étape.

## Règles

- Téléphone obligatoire.
- H = Homme, F = Femme.
- `X` pour l'email utilise `DEFAULT_MEMBER_EMAIL`.
- Type d'adhérent par défaut : `DEFAULT_MEMBER_TYPE_ID`.
- Nature : personne physique (`morphy=mor`).
- Date d'adhésion : aujourd'hui proposée par défaut.
- Aucun appel de création Dolibarr avant `VALIDER`.
- Synchronisation du miroir après création.
- Audit DuckDB après création.

## Important

La date d'adhésion est collectée et auditée dans cette étape.
La création de la cotisation/adhésion et de son écriture complémentaire reste
dans 17A.7.2 afin de ne pas mélanger l'adhérent avec son adhésion financière.

## Tests

```bash
python -m py_compile modules/member_wizard.py
python -m pytest -v
```
