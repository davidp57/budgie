# Budgie 🐦 — Feuille de route

🌐 [English version](../en/roadmap.md)

Ce document présente les améliorations futures prévues pour Budgie.
Les items sont regroupés par priorité et peuvent évoluer.

---

## Court terme

### Corrections & petites améliorations

- [x] **Choix de couleur d'une enveloppe** — permettre aux utilisateurs d'assigner une couleur personnalisée à chaque enveloppe directement depuis la vue budget
- [x] **Plage de montant dans les règles de catégorie** — conditions min/max optionnelles sur une règle d'auto-catégorisation (ex. : seulement les transactions entre −50 € et −5 €)
- [x] **Type de transaction dans les règles de catégorie** — filtrer par débit, crédit ou tous
- [x] **Bouton effacer la recherche** — icône ✕ pour vider rapidement le filtre texte dans la vue pointage
- [x] **Option de création de règle dans le wizard de pointage** — lors de la liaison bancaire, choisir si une règle de catégorisation doit être créée ou non
- [x] **Durcissement sécurité** — rate limiting sur les endpoints d'auth, liste noire JWT, headers de sécurité stricts, bcrypt 10→12 rounds, limite de taille des requêtes, sanitisation HTML des saisies libres
- [x] **Dock mobile masqué** — `z-50`, `viewport-fit=cover` et padding `safe-area-inset-bottom` pour que le dock ne cache plus le contenu sur iPhone
- [x] **Correction du démarrage** — répertoire `data/` créé automatiquement avant les migrations au premier lancement
- [x] **Tableau de bord des dépenses par groupe** — la vue Dépenses regroupe par groupe de catégories avec drill-down par enveloppe
- [x] **Métriques budgétaires** — les cartes d'enveloppe affichent le nombre de dépenses et le nombre de dépenses hors budget
- [x] **Édition des dépenses** — modifier date, montant, description, catégorie, enveloppe ou supprimer depuis la page Dépenses
- [x] **Dépense rapide sans catégorie** — la saisie rapide lie directement à une enveloppe ; dépenses hors budget saisissables depuis la bannière Budget
- [x] **Fichiers de contribution & tutoriels** — `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, tutoriels d'installation et de prise en main (EN + FR)
- [x] **Chiffrement au repos** — noms de bénéficiaires, mémos et descriptions chiffrés côté serveur avec AES-256-GCM ; données existantes migrées automatiquement au démarrage
- [x] **Héritage automatique du budget** — les montants budgétés se reportent automatiquement d’un mois à l’autre ; une icône `↩` signale tout montant hérité dans l’interface- [x] **Déverrouillage par passkey (PRF)** — la connexion par passkey (Face ID / Touch ID) déverrouille automatiquement le chiffrement de bout en bout via l'extension WebAuthn PRF ; plus de PIN ni de phrase secrète après la première connexion
### Vue des dépenses par catégorie

- [ ] Nouvelle vue dédiée affichant les dépenses pointées (rapprochées) par catégorie et par groupe pour un mois sélectionné
- [ ] Afficher le budget prévu vs. réalisé en regard des totaux d'enveloppe
- [ ] Filtrer par compte ou par plage de dates

### Apprentissage passif

Améliorer la précision de la catégorisation en apprenant du comportement utilisateur.

- [ ] Proposer la mise à jour de `Payee.auto_category_id` lors d'une catégorisation manuelle
- [ ] Proposer la création d'une `CategoryRule` depuis des affectations manuelles répétées
- [ ] Suivre les métriques de précision de la catégorisation

### Améliorations UX

- [ ] Recherche de transactions (texte intégral sur bénéficiaire, mémo)
- [ ] Édition de transactions en masse (sélection multiple + affecter une catégorie)
- [ ] Raccourcis clavier pour les actions courantes

---

## Moyen terme

### Refonte de la vue transactions

La vue liste des transactions actuelle est devenue moins utile depuis que le rapprochement couvre la majorité des flux quotidiens. La refondre autour de ce qui reste pertinent :

- [ ] Transformer en journal de recherche global (texte intégral, plage de dates, catégorie, compte)
- [ ] Édition en ligne de la catégorie, du mémo et du montant directement dans la liste
- [ ] Actions en masse : assigner une catégorie, supprimer, exporter la sélection
- [ ] Distinction visuelle claire entre transactions pointées et non pointées

### Amélioration de la gestion des catégories

- [ ] Réordonner les groupes et les catégories par glisser-déposer
- [ ] Renommer une catégorie ou un groupe en ligne
- [ ] Déplacer une catégorie d'un groupe vers un autre
- [ ] **Diviser** une catégorie en deux (redistribuer les transactions passées)
- [ ] **Fusionner** deux catégories en une (réaffecter toutes les transactions)

### Rapports

- [ ] Ventilation mensuelle des dépenses par catégorie (graphiques)
- [ ] Évolution des revenus vs. dépenses dans le temps
- [ ] Historique de respect du budget (% d'enveloppes restant positives)
- [ ] Export des rapports en CSV/PDF

### Multi-devise

- [ ] Support de plusieurs devises par compte
- [ ] Gestion des taux de change

### Transactions récurrentes

- [ ] Définir des modèles de transactions récurrentes (loyer, abonnements…)
- [ ] Générer automatiquement des transactions virtuelles depuis les plannings récurrents
- [ ] Notifications pour les transactions récurrentes à venir

---

## Long terme

### Données & Synchronisation

- [ ] Support PostgreSQL en alternative à SQLite
- [ ] Améliorations de la synchronisation multi-appareils
- [ ] Export/import de données (sauvegarde complète en JSON/ZIP)

### Budget avancé

- [ ] Objectifs d'épargne avec suivi de progression
- [ ] Règles de report par enveloppe (plafonné ou illimité)
- [ ] Suivi des paiements par carte de crédit (enveloppes de dette séparées)

### Intégrations

- [ ] Intégration API bancaire (Open Banking / PSD2) pour les imports automatiques
- [ ] Système de notifications (email/push pour alertes budget)

---

## Terminé

Voir [CHANGELOG.md](../../CHANGELOG.md) pour les fonctionnalités livrées.
