# Déploiement — Yessal Asso Bot

## Procédure de livraison

La procédure opérationnelle du projet reste :

1. recevoir le ZIP contenant uniquement les fichiers modifiés/nouveaux ;
2. extraire dans le dossier local `yessal-asso-bot/` et remplacer les fichiers ;
3. pousser vers le dépôt GitHub `jaxaayannuaire/yessal-asso-bot` avec PowerShell ;
4. mettre à jour le VPS du bot ;
5. redémarrer le service systemd ;
6. consulter les logs et tester au minimum `/start`, `/ping_dolibarr` et `/dashboard` selon les droits disponibles.

## Variables sensibles

Le fichier `.env` ne doit jamais être versionné. Utiliser `.env.example` comme modèle.

## Vérifications après mise à jour

```bash
python3 -m compileall core services modules main.py
sudo systemctl status yessal-asso-bot --no-pager
sudo journalctl -u yessal-asso-bot -n 100 --no-pager
```

Adapter le nom du service si le service systemd installé porte un autre nom.
