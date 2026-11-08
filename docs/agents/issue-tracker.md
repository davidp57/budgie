# Suivi : les tickets GitHub

Les lots, leurs PRD et leurs tickets sont des tickets GitHub du dépôt `davidp57/budgie`, comme pour IronGall.

## Conventions

- Un **lot** est un ticket étiqueté `lot`, titré `<LOT-ID> — <titre>` ; son corps est le PRD (gabarit de PRD de Matt), ses conditions de fin sont des cases à cocher sous `## Done when`.
- Ses **tickets** sont ses sous-tickets, étiquetés `ticket`, titrés `<LOT-ID> NN — <titre>`, numérotés à partir de `01` dans l'ordre des dépendances.
- Le **statut** est une étiquette (voir [triage-labels.md](triage-labels.md)).
- Les identifiants de lot : `FEAT-…`, `FIX-…`, `CHORE-…`, `DOC-…`, `INVESTIGATE-…`, en majuscules, tirets.
- Un ticket qui en bloque un autre est indiqué par la relation « blocked by » de GitHub, et rappelé dans le corps (`Blocked by #N`).
- Un lot = une branche (`feature/`, `fix/` ou `chore/<LOT-ID>`) et une seule PR vers `develop`, qui porte `Closes #<ticket>` pour chacun de ses tickets et `Closes #<lot>`.
  `develop` est la branche par défaut du dépôt : ces mots-clés ferment les tickets à la fusion.
- Le dépôt est public : aucun relevé, montant réel ni nom de commerçant tiré d'un vrai compte dans un ticket.

## Où regarder

- Le PRD de l'application et l'avancement des lots : [#43](https://github.com/davidp57/budgie/issues/43), dont les lots sont les sous-tickets.
- Lots en cours ou en attente : `gh issue list --repo davidp57/budgie --label lot`.
- Lots prêts : `gh issue list --repo davidp57/budgie --label lot --label "⬜ ready"`.
- Ce qui attend David : `gh issue list --repo davidp57/budgie --label "🧑 waiting-human"`.
- Lots terminés : `gh issue list --repo davidp57/budgie --state closed --label lot`.
- La vision longue : `docs/fr/roadmap.md` ; un item n'y devient un lot qu'au moment où on le prend.

## Quand un skill dit « publier dans le tracker »

- Un PRD → un ticket étiqueté `lot` et `⬜ ready`, titré `<LOT-ID> — …`, rattaché comme sous-ticket au PRD #43 (`gh api -X POST repos/davidp57/budgie/issues/43/sub_issues -F sub_issue_id=<id du ticket>`, l'`id` et non le numéro).
- Un ticket → un ticket étiqueté `ticket` et `⬜ ready`, titré `<LOT-ID> NN — …`, rattaché comme sous-ticket à son lot, avec ses relations « blocked by ».
- Tout ce qui est créé l'est à `⬜ ready`.

## Quand un skill dit « lire le ticket »

`gh issue view <numéro> --repo davidp57/budgie --comments`, et pour un lot ses sous-tickets : `gh api repos/davidp57/budgie/issues/<numéro>/sub_issues`.
David donne d'habitude le numéro du lot ou du ticket.

## Les signalements

Un ticket qui n'est ni un lot ni un ticket (un bug signalé, une suggestion, un constat noté en passant) est un signalement, pas un lot.
Quand on le prend en charge, on crée le lot qui le traite et on ferme le signalement en pointant vers lui ; un signalement qui reste ouvert veut dire « noté, personne ne l'a pris ».
