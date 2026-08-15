# Intégration 17A.5
Ajouter `modules/telegram_link.py` et la table `telegram_link_tokens`.
Dans `modules/roles.py`, ajouter `/generer_lien <ID_DOLIBARR>` (Super Admin) et conserver `/lier` comme commande de rapprochement sécurisée.
Dans `main.py`, enregistrer les deux handlers.
Remplacer le lien direct `/lier_moi` par une procédure par jeton.
Pour `ROLE_SUPER_ADMIN`, le menu doit exposer toutes les commandes fonctionnelles, car sa permission est `*`.
Ne pas supprimer les fonctionnalités existantes.
