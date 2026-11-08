---
name: release
description: Sortir une nouvelle version de Budgie (numéro, entretien avec David, RELEASE_NOTES.md, CHANGELOG, version de pyproject.toml, PR develop puis main). À utiliser quand David demande une release ou /release.
---

# Release de Budgie

Tu guides David pas à pas pour sortir une nouvelle version de Budgie, sur le modèle du `/release` d'IronGall.
Une étape à la fois : là où une étape attend une réponse de David, tu t'arrêtes et tu attends.

---

## Le contexte

- `develop` reçoit le travail par des PR ; `main` ne reçoit que des releases.
- Une release, ce sont deux PR :
  1. `chore/RELEASE-X.Y.Z` → `develop` : le numéro, le CHANGELOG, les notes ;
  2. `develop` → `main`, titrée `Release X.Y.Z`, fusionnée par un **vrai commit de fusion** (jamais en squash : `main` et `develop` doivent garder une histoire commune).
- La publication est automatique : à la fusion dans `main`, `.github/workflows/docker.yml` construit l'image, la teste (`/api/health`), la pousse sur GHCR (`ghcr.io/davidp57/budgie:latest` et `:X.Y.Z`), crée le tag `vX.Y.Z` et publie la release GitHub avec `RELEASE_NOTES.md` tel qu'il est dans le commit fusionné.
  Une version `0.x` sort en pré-release.
  Pas de tag à pousser à la main.
- Le workflow refuse de publier si le titre de `RELEASE_NOTES.md` n'est pas exactement `# Budgie — X.Y.Z` pour la version de `pyproject.toml`.
  Une fusion dans `main` dont la version a déjà son tag ne publie rien.
- La version n'existe qu'à un endroit, `pyproject.toml` : le backend la lit dans les métadonnées du paquet, le frontend sur `/api/health`.
- Les PR de lot écrivent leurs entrées sous `## [Unreleased]` et ne touchent jamais la version : le commit de release est le seul endroit où elle bouge.
  `tests/test_changelog.py` le garde.

---

## Étape 1 : ce qui part

1. `git fetch` puis `git pull --ff-only` sur `develop`.
2. Lis la section `## [Unreleased]` de `CHANGELOG.md`, et la liste des PR fusionnées depuis la dernière release (`gh pr list --state merged --base develop`, à partir de la date de la dernière release, `gh release list`).
   Signale ce qui manque au CHANGELOG, s'il manque quelque chose.
3. Vérifie que rien n'attend : PR ouvertes vers `develop`, lots `🔄 in-progress` ou `🧑 waiting-human` qui devraient partir avec cette version.
   Ne décide pas à la place de David : liste-les, avec ta reco.
4. Repère ce qu'un utilisateur doit faire en mettant à jour : migration de base, variable d'environnement nouvelle ou obligatoire, déconnexion forcée, donnée effacée.
5. Propose le numéro, avec ta raison : mineur (`0.10.0`) s'il y a du « Added », du « Changed » ou du « Removed », correctif (`0.9.2`) s'il n'y a que du « Fixed ».

**Attends** que David valide le numéro.

## Étape 2 : l'entretien

Trois questions, **une à la fois**, chacune avec ta reco tirée du CHANGELOG :

1. Quel est le thème de cette version, ce qu'un utilisateur doit en retenir ?
2. Y a-t-il une rupture à signaler : un geste à faire avant de mettre à jour (`.env`, sauvegarde de la base), une fonction retirée, une reconnexion forcée ?
3. Faut-il mettre en avant une contribution ou un point précis ?

## Étape 3 : les notes de version

1. Écris le contenu complet de `RELEASE_NOTES.md`, sur le modèle de la version précédente (`git show origin/main:RELEASE_NOTES.md` ; la branche `main` locale n'est pas tenue à jour) :
   - titre exactement `# Budgie — X.Y.Z` (`docker.yml` et `test_changelog.py` le contrôlent) ;
   - en français d'abord, pour les utilisateurs, puis la même chose en anglais sous `## 🇬🇧 In English` ;
   - une phrase d'accroche, puis des sections par thème avec un emoji, des puces qui disent ce que l'utilisateur y gagne ;
   - une rupture en tête, sous « ⚠️ Avant de mettre à jour », avec le geste exact.
2. Retire le bruit technique (refactors, tests, CI, outillage) : ne garde que ce qui change pour celui qui s'en sert.
   Pas de vocabulaire d'implémentation, et le vocabulaire de l'application tel qu'il est à l'écran (enveloppes, pointage, transactions virtuelles…).
3. Propose le texte à David.

**Attends** sa validation ou ses corrections.

## Étape 4 : la clôture

Une fois les notes validées :

1. **`RELEASE_NOTES.md`** : le texte validé.
2. **`CHANGELOG.md`** : `## [Unreleased]` devient `## [X.Y.Z] - AAAA-MM-JJ` (date du jour), et une section `## [Unreleased]` **vide** est rouverte au-dessus.
   Sans elle, la PR suivante n'a nulle part où écrire.
3. **La version** : `version` dans `pyproject.toml`.
4. **Le README** : s'il cite une version ou une fonction qui a changé, le mettre à jour.
5. **Les vérifications** : toute la porte de qualité de `AGENTS.md` (`test_changelog.py` compris), puis `docker compose build`, qui doit aboutir.

## Étape 5 : les deux PR

1. Crée `chore/RELEASE-X.Y.Z` depuis `develop`, committe (`chore(release): X.Y.Z`), pousse, ouvre la PR vers `develop`, titrée `Release X.Y.Z (develop)`.
2. Comme toute PR : `pr-code-review`, CI verte, puis fusion.
3. Ouvre la PR `develop` → `main`, titrée `Release X.Y.Z`.
   Attends la CI verte, puis **demande le feu vert de David** pour fusionner : c'est la fusion qui publie, et elle ne se reprend pas (une image `latest` que son NAS peut tirer, un tag et une release publiés).
4. Fusionne avec un commit de fusion : `gh pr merge <n> --merge`.

## Étape 6 : le contrôle

1. Le workflow « CI-Docker » sur `main` : il doit avoir construit, testé et publié, pas seulement tourné (`gh run list --workflow docker.yml --branch main`, puis `gh run view`).
2. La release : `gh release view vX.Y.Z` doit avoir les notes ; l'image `ghcr.io/davidp57/budgie:X.Y.Z` doit exister.
3. Reviens sur `develop` et fais `git pull`.

Rends compte à David en une ligne par point, avec les liens.
