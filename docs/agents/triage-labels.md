# Étiquettes de statut et rôles de tri

Une seule étiquette de statut à la fois, sur chaque lot et chaque ticket ouvert.
Les rôles de tri des skills de Matt s'y rapportent ainsi :

| Statut | Étiquette ou état | Rôle(s) de tri de Matt |
|---|---|---|
| prêt | `⬜ ready` | ready-for-agent |
| en attente d'un humain | `🧑 waiting-human` | ready-for-human, needs-info |
| abandonné | fermé « not planned » (🚫 won't fix), étiquette `wontfix` | wontfix |

États du cycle de vie, sans équivalent de tri : `🔄 in-progress`, `⏸ paused`, et fermé « completed » (✅ done).

`⏸ paused` veut dire **mis de côté exprès** : le travail est spécifié et pourrait commencer, mais on a décidé de ne pas continuer pour l'instant.
Ce n'est pas `🧑 waiting-human`, qui dit qu'un humain *bloque* (une vérification dans l'application, une question, une ressource qu'il détient) ; pour un ticket en pause, on n'attend rien de personne.
La raison de la pause s'écrit en commentaire au moment où on la pose : une pause sans raison ne se distingue pas d'un oubli.

`needs-triage` n'est pas utilisé : les lots sont créés déjà spécifiés.

Quand le statut change, on retire l'ancienne étiquette en posant la nouvelle :

```bash
gh issue edit <numéro> --repo davidp57/budgie --remove-label "⬜ ready" --add-label "🔄 in-progress"
```
