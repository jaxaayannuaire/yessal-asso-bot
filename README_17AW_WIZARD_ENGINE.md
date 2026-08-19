# Yessal Asso Bot — 17A.W Wizard Engine

Socle conversationnel réutilisable pour tous les composants du bot.

## Gère

- état temporaire par utilisateur Telegram ;
- étapes séquentielles ;
- validation de saisie ;
- boutons inline ;
- récapitulatif ;
- modification d'un champ ;
- validation ;
- annulation ;
- protection contre le double clic au niveau de la session.

## Architecture

Le moteur ne connaît ni Dolibarr ni la caisse.

Chaque module métier fournit :
- ses étapes ;
- ses validateurs ;
- ses boutons ;
- son récapitulatif ;
- sa fonction `on_confirm`.

Voir `MAIN_PY_PATCH_17AW_WIZARD_ENGINE.txt`.

Prochaine étape : `17A.7.1` — inscription interactive d'un adhérent.
