# Budgie 🐦 — Guide Utilisateur

## Table des matières

1. [Qu'est-ce que Budgie ?](#quest-ce-que-budgie-)
2. [Fonctionnalités](#fonctionnalités)
3. [Premiers pas](#premiers-pas)
4. [Gérer les comptes](#gérer-les-comptes)
5. [Gérer les catégories](#gérer-les-catégories)
6. [Importer des transactions bancaires](#importer-des-transactions-bancaires)
7. [Consulter et catégoriser les transactions](#consulter-et-catégoriser-les-transactions)
8. [Le budget (enveloppes)](#le-budget-enveloppes)
9. [Transactions virtuelles (prévisions)](#transactions-virtuelles-prévisions)
10. [Thème et installation mobile](#thème-et-installation-mobile)

---

## Qu'est-ce que Budgie ?

Budgie est une **application de gestion de budget personnel auto-hébergée** qui fonctionne entièrement sur votre propre serveur — pas de service cloud tiers, pas d'abonnement.

Elle suit la méthode du **budget par enveloppes** : chaque centime de revenu est affecté à une catégorie de dépenses avant d'être dépensé. En regardant n'importe quelle catégorie, vous savez immédiatement combien il vous reste.

---

## Fonctionnalités

| Fonctionnalité | Description |
|---|---|
| Import bancaire | Importez des fichiers CSV, Excel, QIF ou OFX exportés depuis votre banque |
| Catégorisation automatique | Les transactions sont catégorisées automatiquement selon l'historique des bénéficiaires et les règles que vous définissez |
| Budget par enveloppes | Attribuez un budget à chaque catégorie chaque mois ; suivez ce qui est disponible |
| Transactions virtuelles | Planifiez des achats futurs pour voir leur impact sur le budget avant qu'ils ne se produisent |
| Historique des transactions | Filtrez par compte, type (réel / prévision) et recherche |
| Thème sombre / clair | Bascule automatiquement selon les préférences système, ou changez manuellement |
| Compatible mobile | Peut être ajouté à l'écran d'accueil du téléphone (PWA) |

---

## Premiers pas

### Accéder à l'application

Ouvrez `http://VOTRE_SERVEUR:8080` dans votre navigateur (ou `http://localhost:5173` en mode développement).

À votre première visite, cliquez sur **S'inscrire** pour créer votre compte.

### Ordre de configuration recommandé

1. **Créer les comptes** — vos comptes bancaires, épargne, etc.
2. **Créer les groupes de catégories et les catégories** — ex. groupe *Logement* avec les catégories *Loyer*, *Électricité*, *Internet*
3. **Importer votre premier fichier bancaire**
4. **Définir votre budget** pour le mois en cours

---

## Gérer les comptes

Allez dans **Paramètres → Comptes**.

Chaque compte a :
- Un **nom** (ex. « Compte courant », « Épargne »)
- Un **type de compte** (courant, épargne, carte de crédit…)

Les soldes des comptes sont calculés depuis la somme de toutes les transactions non-virtuelles.

> **Conseil** : Créez un compte par compte bancaire réel. Ne mélangez pas différentes banques dans un seul compte.

---

## Gérer les catégories

Allez dans **Paramètres → Catégories**.

Les catégories sont organisées en **groupes** (ex. *Logement*, *Alimentation*, *Transport*).

| Terme | Signification |
|---|---|
| Groupe | Un regroupement logique de catégories (ex. « Logement ») |
| Catégorie | Un poste de dépense unique (ex. « Loyer ») |

### Règles de catégorisation automatique

Dans **Paramètres → Règles**, vous pouvez définir des règles pour assigner automatiquement une catégorie lorsqu'une transaction correspond à un motif.

Chaque règle contient :
- **Champ** : rechercher dans le nom du bénéficiaire ou le mémo/description
- **Type de correspondance** : contient un mot, correspondance exacte ou expression régulière
- **Catégorie** : la catégorie à assigner quando la règle correspond
- **Priorité** : les règles avec une priorité plus haute sont évaluées en premier

Une fois une transaction catégorisée, le nom du bénéficiaire est mémorisé — les futures transactions du même bénéficiaire sont catégorisées automatiquement.

---

## Importer des transactions bancaires

Allez dans **Import**.

### Étape 1 — Téléverser un fichier

Sélectionnez votre fichier bancaire. Formats supportés :
- **CSV** — la plupart des banques proposent un export CSV ; les colonnes sont détectées automatiquement
- **Excel** (.xlsx / .xls)
- **QIF** — format ancien, très répandu
- **OFX / OFC** — format d'échange ouvert utilisé par de nombreuses banques européennes

### Étape 2 — Prévisualisation

Après le téléversement, vous voyez un aperçu de toutes les transactions détectées. Vérifiez que :
- Les dates, montants et descriptions semblent corrects
- Les catégories ont été assignées automatiquement là où c'est possible (vous pouvez les corriger ici)

### Déduplication

Budgie calcule une empreinte unique pour chaque transaction (basée sur la date, le montant et la description). Si vous importez le même fichier deux fois, aucun doublon n'est créé.

### Correspondance avec les prévisions

Si vous avez créé des **transactions virtuelles** (prévisions) qui correspondent aux transactions réelles du fichier, Budgie suggère de les lier automatiquement. Une suggestion apparaît quand :
- Les montants sont à moins de 10% l'un de l'autre
- Les dates sont à moins de 60 jours l'une de l'autre

Acceptez la suggestion pour marquer la prévision comme **réalisée**.

### Étape 3 — Confirmer

Cliquez sur **Confirmer l'import**. Toutes les transactions sont sauvegardées ; les prévisions liées sont marquées comme réconciliées.

---

## Consulter et catégoriser les transactions

Allez dans **Transactions**.

### Filtres

| Filtre | Options |
|---|---|
| Compte | Tous les comptes ou un compte spécifique |
| Type | Tout / Réels seulement / Prévisions seulement |

### Assigner une catégorie

Cliquez sur la cellule catégorie d'une transaction pour ouvrir le sélecteur de catégories. Sélectionnez la catégorie correcte et sauvegardez.

---

## Le budget (enveloppes)

Allez dans **Budget**.

### Comment ça marche

Chaque catégorie a trois valeurs pour le mois en cours :

| Valeur | Signification |
|---|---|
| **Budgété** | Le montant que vous avez décidé d'allouer à cette catégorie ce mois |
| **Activité** | Le total de toutes les transactions (y compris les prévisions) dans cette catégorie ce mois |
| **Disponible** | Budgété − Activité, reporté des mois précédents |

Un **Disponible positif** signifie qu'il vous reste de l'argent à dépenser. Un **Disponible négatif** signifie que vous avez dépassé le budget.

### À budgéter

En haut de la page budget, **À budgéter** montre votre revenu total moins tout ce que vous avez déjà affecté aux catégories. L'objectif est **zéro** — chaque centime doit être affecté quelque part.

### Allocations mensuelles

Cliquez sur la cellule **Budgété** d'une catégorie pour saisir le montant à allouer pour ce mois. Les modifications sont sauvegardées automatiquement.

> **Conseil** : Les prévisions (transactions virtuelles) réduisent le montant Disponible même avant que la vraie transaction n'arrive. C'est intentionnel — cela vous permet de voir l'impact réel des dépenses planifiées.

---

## Transactions virtuelles (prévisions)

Une **transaction virtuelle** (ou prévision) vous permet de planifier un achat futur et de voir immédiatement son impact sur le budget.

### Créer une prévision

Dans la vue **Transactions**, cliquez sur le bouton ⏳ **Nouvelle prévision**.

Remplissez :
- **Montant** (en euros, ex. `49,99`)
- **Date estimée**
- **Catégorie**
- **Mémo** (description facultative)
- **Compte** (le compte qui sera débité)

La prévision apparaît dans la liste des transactions avec une icône ⏳ et un style en pointillé. Le montant **Disponible** du budget pour cette catégorie est immédiatement réduit.

### Quand la vraie transaction arrive

Lorsque vous importez votre relevé bancaire et que la transaction réelle correspondante est trouvée, Budgie suggère de la lier à la prévision. Acceptez la suggestion pour :
- Marquer la prévision comme **réconciliée** (elle disparaît de la liste des prévisions non liées)
- Maintenir l'exactitude de votre budget

### Prévisions non liées

Dans la vue Transactions, filtrez sur **Prévisions** pour voir toutes les prévisions en attente (non réalisées).

---

## Thème et installation mobile

### Thème sombre / clair

Cliquez sur le bouton ☀️ / 🌙 en haut à gauche de la barre latérale pour basculer entre les thèmes clair et sombre. Votre choix est sauvegardé et appliqué à votre prochaine visite.

Le thème est également défini automatiquement au premier chargement selon les préférences de votre système d'exploitation (mode sombre ou clair).

### Ajouter à l'écran d'accueil (PWA)

Sur mobile (Android / iOS), ouvrez Budgie dans votre navigateur et utilisez l'option **Ajouter à l'écran d'accueil** dans le menu du navigateur. L'application s'ouvrira alors en plein écran comme une application native.
