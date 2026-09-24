# 05 — Stop + Delete d'un run (`POST .../stop`, `DELETE /api/ephemeral/runs/{id}`)

Réf design : `docs/ephemeral-api.md`

## Contexte

Besoin explicite : pouvoir arrêter complètement un run en cours, et le supprimer immédiatement (sans attendre le TTL), indépendamment l'un de l'autre.

## Objectif

### `POST /api/ephemeral/runs/{id}/stop`

- Réutilise le mécanisme de stop existant (`POST /api/dossiers/{id}/stop`, `backend/app/routers/dossiers.py:203`) pour couper l'exécution Celery en cours.
- Passe le `Dossier` en statut `arrêté`.
- Déclenche la pose de `dossier_ephemere.expires_at = ended_at + ttl_hours` (si `persist=false`) — logique commune avec la fin normale du pipeline, cf. issue 06.
- N'efface rien : le run reste consultable via `GET`, et sera purgé normalement au TTL (ou supprimable manuellement via `DELETE`).

### `DELETE /api/ephemeral/runs/{id}`

- Si le run est encore `en_cours`/`en_attente` : l'arrête d'abord (même effet que `POST .../stop`).
- Supprime ensuite immédiatement le `Dossier` (documents, execution_steps, résultats, fichiers S3) via `delete_dossier` (issue 02) + la ligne `dossier_ephemere`.
- Suppression immédiate, sans attendre `expires_at`. Ne touche pas à l'analyse liée (`analyse_ephemere` conservée, seul `last_run_ended_at` déjà à jour si applicable).
- 404 si `{id}` n'a pas de ligne `dossier_ephemere`.

## Critères d'acceptation

- [ ] `POST .../stop` sur un run `en_cours` coupe bien l'exécution Celery et passe le statut à `arrêté`.
- [ ] `POST .../stop` sur un run déjà terminé est un no-op (ou 409, à trancher en review de code — pas bloquant pour le design).
- [ ] `DELETE` sur un run en cours : stoppe puis supprime, dans une seule transaction logique côté client (un seul appel suffit).
- [ ] `DELETE` sur un run déjà terminé : supprime directement, sans passer par le stop.
- [ ] Fichiers S3 et lignes DB bien supprimés après `DELETE` (test de bout en bout).
- [ ] Tests couvrant : stop sur run en cours, delete sur run en cours, delete sur run terminé, delete sur id inexistant.

## Fichiers concernés

- `backend/app/routers/ephemeral.py`
- `backend/app/routers/dossiers.py` (réutilisation du stop existant)
- `backend/app/repositories/dossier_repository.py` (`delete_dossier`, issue 02)

## Dépendances

Dépend de #20, #21, #23.
