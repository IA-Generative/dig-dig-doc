# 06 — Calcul et pose du TTL (`expires_at`)

Réf design : `docs/ephemeral-api.md`

## Contexte

Principe central du design : le TTL ne démarre **pas** à la création de la ressource mais **à la fin de l'analyse**. Tant qu'un run est en cours (y compris en attente dans la queue Celery), `expires_at` doit rester `NULL` — on ne veut jamais purger un run qui n'a pas fini, même s'il traîne longtemps en file d'attente.

```
expires_at = ended_at + ttl_hours   (posé au moment où le statut passe à un état terminal)
```

## Objectif

1. **Sur `dossier_ephemere`** : dès qu'un `Dossier` associé passe à un statut terminal (`terminé`, `échec`, `arrêté` — y compris suite à un `stop` manuel, issue 05), et si `persist=false` :
   - Poser `dossier_ephemere.expires_at = Dossier.ended_at + dossier_ephemere.ttl_hours`.
   - À faire directement dans le code qui marque le run terminé — le callback worker → `/api/internal/*` (`backend/app/routers/internal.py`) pour la fin normale du pipeline, et l'endpoint `stop` pour l'arrêt manuel. Pas de calcul en batch différé : la pose doit être immédiate et fiable.
2. **Sur `analyse_ephemere`** (si le run référence une analyse éphémère, `dossier_ephemere.analyse_ephemere_id` non nul) :
   - Mettre à jour `analyse_ephemere.last_run_ended_at = Dossier.ended_at`.
   - Recalculer `analyse_ephemere.expires_at = last_run_ended_at + ttl_hours` (le TTL de l'analyse suit celui du dernier run l'ayant utilisée — si plusieurs runs référencent la même analyse éphémère, `expires_at` recule à chaque nouveau run terminé).
   - Si `persist=true` sur l'analyse : `expires_at` reste toujours `NULL`, quel que soit ce qui se passe côté runs.
3. **Validation à la création** (`ttl_hours` en query/body, issue 04) : défaut 24h, rejet (400) si > 17520h (2 ans). Pas de `PATCH` pour prolonger un TTL déjà posé — figé une fois calculé.

## Critères d'acceptation

- [ ] `expires_at` reste `NULL` tant que le `Dossier` n'a pas atteint un statut terminal.
- [ ] `expires_at` posé correctement à `ended_at + ttl_hours` dans les 3 chemins de fin de run : succès, échec, stop manuel.
- [ ] `analyse_ephemere.expires_at` recalculé correctement à chaque run terminé qui la référence, y compris avec plusieurs runs successifs.
- [ ] `persist=true` (sur l'analyse ou sur le run) empêche toute pose d'`expires_at`, quel que soit l'état.
- [ ] Rejet 400 si `ttl_hours` demandé dépasse 17520.
- [ ] Aucun endpoint de modification de TTL après création.
- [ ] Tests unitaires sur le calcul, y compris cas limites (run échoué, run stoppé, plusieurs runs sur la même analyse éphémère).

## Fichiers concernés

- `backend/app/routers/internal.py` (callback worker → fin de run)
- `backend/app/routers/ephemeral.py` (endpoint stop)
- `backend/app/repositories/dossier_repository.py`
- `backend/app/repositories/analyse_repository.py`

## Dépendances

Dépend de #20, #23, #24.
