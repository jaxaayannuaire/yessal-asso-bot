# Yessal Asso Bot — CODEX Context

## 1. Purpose

Yessal Asso Bot est un assistant Telegram destiné principalement à la gestion opérationnelle d'une association.

Le bot sert notamment le trésorier et les responsables de l'association, tout en fournissant aux adhérents des informations et notifications utiles.

Le bot doit rester modulaire, maintenable, sécurisé et évolutif.

---

## 2. Rôle de Codex

Codex est l'agent de développement du projet.

Il doit :

- analyser le code existant avant toute modification ;
- implémenter les tâches qui lui sont explicitement confiées ;
- respecter l'architecture existante ;
- modifier uniquement les fichiers nécessaires ;
- exécuter les tests disponibles ;
- signaler clairement les fichiers modifiés/créés/supprimés ;
- signaler tout problème ou conflit avant de prendre une décision architecturale.

Codex n'est pas l'autorité architecturale du projet.

Toute modification importante de l'architecture doit être validée avant implémentation.

---

## 3. Architecture générale

Architecture cible actuelle :

```text
yessal-asso-bot/
├── main.py
├── core/
├── services/
├── modules/
├── jobs/
├── tests/
├── docs/
└── ...
```

### core/

Contient les composants fondamentaux et transversaux du bot :

- configuration ;
- sécurité ;
- gestion des utilisateurs/rôles ;
- composants communs ;
- infrastructure interne.

### services/

Contient les services techniques réutilisables :

- API REST Dolibarr ;
- accès DuckDB ;
- synchronisation ;
- notifications ;
- autres intégrations externes.

### modules/

Contient les fonctionnalités métier.

Exemples :

- adhérents / contacts ;
- membres ;
- adhésions ;
- cotisations ;
- caisse ;
- dons ;
- projets ;
- statistiques ;
- dashboard ;
- notifications.

### jobs/

Contient les tâches planifiées et traitements automatiques :

- synchronisation Dolibarr ;
- rappels ;
- alertes ;
- rapports périodiques ;
- autres traitements planifiés.

### tests/

Contient les tests automatisés.

---

## 4. Stack technique

Stack actuelle/prévue :

- Python ;
- Telegram Bot API ;
- DuckDB comme miroir/base locale du bot ;
- Dolibarr REST API comme système métier principal ;
- Git/GitHub pour le versionnement ;
- VPS Linux pour l'exécution en production.

Dolibarr est particulièrement important dans ce projet : il constitue la source métier principale pour les données associatives qui lui sont confiées.

DuckDB sert notamment à disposer d'un miroir local permettant des traitements, statistiques et consultations efficaces sans solliciter inutilement l'API Dolibarr.

---

## 5. Principes fonctionnels

Le bot est principalement utilisé par :

### Trésorier / responsables

Fonctions envisagées :

- suivi des adhérents ;
- suivi des adhésions ;
- suivi des cotisations ;
- gestion et suivi de la caisse ;
- dons ;
- projets ;
- statistiques ;
- tableaux de bord ;
- alertes ;
- rapports périodiques ;
- consultation de données Dolibarr.

### Adhérents

Fonctions envisagées :

- consultation de leur situation ;
- balance / situation financière ;
- statistiques personnelles ou associatives selon les droits ;
- alertes de cotisation ;
- rappels de renouvellement ;
- notifications concernant les projets ;
- autres notifications Telegram pertinentes.

---

## 6. Gestion des rôles

Le système doit respecter les permissions et rôles.

Ne jamais permettre à un utilisateur de consulter ou modifier des informations auxquelles son rôle ne lui donne pas accès.

Toute nouvelle fonctionnalité doit préciser :

- les rôles autorisés ;
- les actions autorisées ;
- les données visibles ;
- les actions interdites.

Ne jamais contourner le système de permissions existant.

---

## 7. Dolibarr

Dolibarr est une dépendance métier majeure.

Lorsqu'une fonctionnalité utilise Dolibarr :

1. rechercher d'abord les services/API Dolibarr existants ;
2. réutiliser les abstractions existantes ;
3. éviter de créer un second mécanisme d'accès à Dolibarr ;
4. gérer correctement les erreurs API ;
5. éviter les appels inutiles ;
6. ne jamais exposer de credentials ;
7. ne jamais modifier directement la base de production Dolibarr sauf décision explicite.

Les identifiants et tokens Dolibarr doivent rester dans les variables d'environnement ou mécanismes de configuration sécurisés.

---

## 8. DuckDB

DuckDB est utilisé comme miroir local pour les besoins du bot.

Principes :

- ne pas considérer DuckDB comme la source métier principale lorsque Dolibarr est la source de référence ;
- conserver une stratégie de synchronisation cohérente ;
- gérer les données absentes ou supprimées ;
- éviter les doublons ;
- préserver les identifiants permettant la correspondance avec Dolibarr ;
- ne pas modifier arbitrairement le schéma existant sans vérifier les dépendances.

Toute modification du schéma doit être traitée avec prudence et accompagnée de tests.

---

## 9. Telegram

Le bot doit respecter l'architecture Telegram existante.

Lors de l'ajout d'une fonctionnalité :

- réutiliser les handlers/services existants ;
- respecter les conventions de navigation ;
- préserver les boutons et menus existants ;
- ne pas casser les conversations ou callbacks existants ;
- respecter les permissions ;
- gérer proprement les erreurs utilisateur ;
- éviter les messages Telegram excessivement verbeux.

Les tokens Telegram ne doivent jamais être écrits dans le code.

---

## 10. Notifications et jobs

Les traitements automatiques doivent être conçus pour être :

- idempotents lorsque nécessaire ;
- résistants aux erreurs réseau ;
- journalisés ;
- contrôlables ;
- testables.

Une tâche planifiée ne doit pas envoyer plusieurs fois la même notification simplement parce qu'elle a été relancée.

Les jobs doivent gérer correctement les indisponibilités temporaires de Dolibarr ou Telegram.

---

## 11. Règle de modification minimale

Principe obligatoire :

> Modifier le minimum de fichiers nécessaire pour réaliser la tâche.

Ne pas :

- refactoriser inutilement ;
- renommer massivement des fichiers ;
- changer les conventions existantes ;
- remplacer une bibliothèque sans nécessité ;
- modifier des modules non concernés ;
- supprimer du code fonctionnel existant.

Une amélioration hors périmètre doit être signalée séparément et non implémentée automatiquement.

---

## 12. Fichiers sensibles

Ne jamais modifier ou exposer sans autorisation explicite :

- `.env` ;
- secrets ;
- tokens Telegram ;
- credentials Dolibarr ;
- mots de passe ;
- clés API ;
- clés SSH ;
- credentials de base de données ;
- secrets de production.

Ne jamais copier de secrets dans :

- le code ;
- les tests ;
- les logs ;
- les commits ;
- la documentation ;
- les réponses finales.

---

## 13. Git et GitHub

Le dépôt GitHub du projet est :

`https://github.com/jaxaayannuaire/yessal-asso-bot`

La branche principale doit rester protégée contre les modifications non validées.

Règles :

- pas de force push ;
- pas de suppression de branche sans autorisation ;
- pas de modification directe de `main` sans validation ;
- examiner le diff avant livraison ;
- ne jamais committer de secrets.

Le workflow de livraison officiel reste contrôlé par le propriétaire du projet.

---

## 14. Procédure de livraison officielle

La procédure de livraison à respecter est :

```text
Développement
    ↓
Tests
    ↓
Review du diff
    ↓
Liste des fichiers modifiés/nouveaux
    ↓
ZIP contenant uniquement ces fichiers
    ↓
Écrasement dans le dossier local yessal-asso-bot
    ↓
Tests locaux
    ↓
Push GitHub via PowerShell
    ↓
Récupération / mise à jour sur le VPS
    ↓
Vérification en production
```

Codex ne doit pas remplacer cette procédure par un déploiement automatique vers le VPS.

---

## 15. Documentation de référence

Avant de modifier le projet, consulter si disponibles :

- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/DECISIONS.md`
- `docs/CODEX-CONTEXT.md`

Ordre de priorité :

1. instructions explicites de la tâche actuelle ;
2. `AGENTS.md` ;
3. documentation d'architecture ;
4. décisions documentées ;
5. code existant ;
6. conventions déduites du code.

En cas de contradiction importante, arrêter l'implémentation et signaler le conflit.

---

## 16. Avant de coder

Pour chaque tâche :

1. inspecter le dépôt ;
2. lire les fichiers de documentation pertinents ;
3. rechercher les fonctions/classes/services existants ;
4. identifier les fichiers réellement concernés ;
5. vérifier les dépendances ;
6. établir un plan minimal ;
7. implémenter uniquement le périmètre demandé.

Ne pas supposer qu'une fonctionnalité n'existe pas avant d'avoir recherché le code.

---

## 17. Après modification

Toujours effectuer autant que possible :

- vérification syntaxique ;
- tests unitaires ;
- tests d'intégration disponibles ;
- vérification des imports ;
- vérification des erreurs évidentes ;
- inspection du diff.

Le rapport final doit contenir :

### Résultat
Résumé de la tâche.

### Fichiers créés
Liste exacte.

### Fichiers modifiés
Liste exacte.

### Fichiers supprimés
Liste exacte, ou `Aucun`.

### Tests
Tests exécutés et résultats.

### Diff
Résumé des changements importants.

### Points d'attention
Problèmes, limitations ou décisions nécessaires.

---

## 18. Critères d'acceptation

Une tâche n'est considérée comme terminée que si :

- la fonctionnalité demandée est implémentée ;
- les fonctionnalités existantes ne sont pas volontairement cassées ;
- les tests disponibles passent ;
- les erreurs connues sont signalées ;
- les fichiers modifiés sont identifiés ;
- aucune donnée sensible n'a été exposée ;
- le diff reste dans le périmètre demandé.

---

## 19. En cas d'incertitude

Ne pas improviser lorsqu'une décision peut avoir un impact important.

S'arrêter et signaler :

- le problème ;
- les fichiers concernés ;
- les options possibles ;
- les conséquences de chaque option.

Demander une validation avant toute modification architecturale ou destructive.

---

## 20. Tâche actuelle

Cette section doit être mise à jour avant chaque nouvelle tâche importante.

### Objectif

À définir.

### Fichiers autorisés

À définir.

### Fichiers interdits

À définir.

### Contraintes

À définir.

### Critères d'acceptation

À définir.

### Tests attendus

À définir.

---

## 21. Règle finale

Yessal Asso Bot est un projet évolutif.

La priorité est :

**stabilité → sécurité → cohérence architecturale → maintenabilité → fonctionnalité → optimisation.**

Ne jamais sacrifier la stabilité de l'existant pour une amélioration non nécessaire.
