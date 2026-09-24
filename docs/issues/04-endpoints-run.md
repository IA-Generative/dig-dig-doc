# 04 — Endpoints run : flux A + flux B (`POST/GET /api/ephemeral/runs`)

Réf design : `docs/ephemeral-api.md`

## Contexte

Deuxième bloc d'endpoints : lancer le pipeline complet (classification → extraction d'entités → agents) sur un ensemble de documents, en réutilisant la création `Dossier` + upload `DossierDocument` + dispatch Celery déjà existants (`backend/app/routers/dossiers.py`, `backend/app/celery_client.py`).

Deux flux d'entrée, même comportement sous-jacent :
- **Flux A** : `analyse_id` dans l'URL (analyse déjà créée à l'étape précédente, issue 03).
- **Flux B** : `analyse_id` dans le body, en un seul appel.

Dans les deux cas, `analyse_id` peut référencer soit une analyse créée via `/api/ephemeral/analyses` (éphémère ou non), soit l'id d'une `Analyse` classique déjà existante sur la plateforme (cas confirmé : relancer une analyse déjà configurée sur des documents jetables, sans la modifier). Dans ce second cas, `dossier_ephemere.analyse_ephemere_id` reste `NULL`.

## Objectif

### `POST /api/ephemeral/analyses/{analyse_id}/runs?ttl_hours=48` (flux A)

- Multipart : fichiers + `persist: bool` (défaut `false`).
- `ttl_hours` en query param : défaut 24h si absent, rejeté (400) si > 17520 (2 ans).
- Réutilise la création `Dossier` + upload `DossierDocument` existante (même code que `dossiers.py`).
- Lie le dossier à `analyse_id` (existant, éphémère ou non).
- Crée la ligne `dossier_ephemere` (`persist`, `ttl_hours`, `analyse_ephemere_id` si applicable).
- Déclenche automatiquement le pipeline complet (équivalent du `launch` existant, `dossiers.py:178`, pas d'étape manuelle séparée).
- Renvoie `{ "run_id": <uuid> }`.

### `POST /api/ephemeral/runs?ttl_hours=48` (flux B)

- Body : `analyse_id` + fichiers (multipart) + `persist`.
- Même comportement que le flux A, sans passer par l'étape de création d'analyse.
- Si `analyse_id` ne correspond à aucune `Analyse` existante (ni classique, ni éphémère) : 404.

### `GET /api/ephemeral/runs/{id}`

- Renvoie le statut (`DossierStatus`) et, une fois `terminé`, les résultats (classification, entités, sorties agents).
- 404 si `{id}` n'a pas de ligne `dossier_ephemere` associée.

## Critères d'acceptation

- [ ] `ttl_hours` validé (défaut 24h, max 17520h, 400 sinon).
- [ ] Flux A et flux B aboutissent au même état final (mêmes lignes créées, même déclenchement pipeline).
- [ ] `analyse_id` référençant une analyse classique de la plateforme fonctionne (pas de ligne `analyse_ephemere` requise côté analyse).
- [ ] Le pipeline se déclenche automatiquement sans appel `launch` séparé.
- [ ] `GET` renvoie le statut en cours puis les résultats complets une fois terminé.
- [ ] Tests couvrant flux A, flux B, et le cas `analyse_id` classique.

## Fichiers concernés

- `backend/app/routers/ephemeral.py`
- `backend/app/routers/dossiers.py` (réutilisation upload + launch)
- `backend/app/celery_client.py` (dispatch pipeline)
- `backend/app/repositories/dossier_repository.py`

## Dépendances

Dépend de #20 et #22.
