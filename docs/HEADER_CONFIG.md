# En-tête organisationnel

Le composant `core/header.py` est réutilisable pour les futures pages du bot.

## Raison sociale

Le composant essaie d'abord la méthode `DolibarrClient.get_organization_info()` si elle existe dans la version du client REST installée.

En secours, ajouter dans `.env` :

```env
DOLIBARR_COMPANY_NAME=Nom de la raison sociale Dolibarr
DOLIBARR_COMPANY_LOGO_URL=https://votre-dolibarr.tld/chemin/vers/le-logo.png
```

Ces valeurs ne sont pas des secrets et peuvent être adaptées ensuite pour une récupération 100 % automatique depuis l'endpoint Dolibarr confirmé par l'explorateur API.

## Limitation Telegram

Telegram ne permet pas d'afficher une image réelle de 80x80 à gauche d'un texte dans le corps d'un message. Le composant envoie donc le logo comme en-tête visuel avant la page lorsque l'URL est disponible.
