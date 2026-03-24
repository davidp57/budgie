# Budgie 🐦 — Feuille de route

🌐 [English version](../en/roadmap.md)

Ce document présente les améliorations futures prévues pour Budgie.
Les items sont regroupés par priorité et peuvent évoluer.

---

## Court terme

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
