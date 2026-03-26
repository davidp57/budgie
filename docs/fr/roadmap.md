# Budgie 🐦 — Feuille de route

🌐 [English version](../en/roadmap.md)

Ce document présente les améliorations futures prévues pour Budgie.
Les items sont regroupés par priorité et peuvent évoluer.

---

## Court terme

### Corrections & petites améliorations

- [x] **Choix de couleur d'une enveloppe** — permettre aux utilisateurs d'assigner une couleur personnalisée à chaque enveloppe directement depuis la vue budget
- [ ] **Plage de montant dans les règles de catégorie** — ajouter des conditions min/max optionnelles lors de la création ou modification d'une règle d'auto-catégorisation (ex. : seulement les transactions entre −50 € et −5 €)

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
