# 03 — Endpoints définition : `POST/GET/DELETE /api/ephemeral/analyses`

Réf design : `docs/ephemeral-api.md`

## Contexte

Premier bloc d'endpoints du nouveau router `ephemeral` : créer/consulter/supprimer la définition d'une analyse (agents, classification, entités), en s'appuyant entièrement sur la création `Analyse` déjà existante (`backend/app/routers/analyses.py`), à laquelle on accroche une ligne `analyse_ephemere` (issue 01).

## Objectif

Nouveau router `backend/app/routers/ephemeral.py`, monté sous `/api/ephemeral`.

### `POST /api/ephemeral/analyses`

- Body : mêmes champs que la création `Analyse` standard (agents, classification, entités/labels, modèle, config output/tools) + `persist: bool` (défaut `false`).
- Réutilise le repository/service de création `Analyse` existant (pas de réimplémentation).
- Crée ensuite la ligne `analyse_ephemere` associée (`persist`, `created_at`).
- Renvoie `{ "analyse_id": <uuid> }` dans tous les cas, que `persist` soit `true` ou `false`.

### `GET /api/ephemeral/analyses/{id}`

- Renvoie la définition complète de l'analyse (agents, classification, entités) — réutilise la lecture `Analyse` existante.
- 404 si `{id}` n'a pas de ligne `analyse_ephemere` associée (cf. scope strict ci-dessous, cohérent avec le comportement du `DELETE`).

### `DELETE /api/ephemeral/analyses/{id}`

- **Scope strict** : ne s'applique qu'aux analyses ayant une ligne `analyse_ephemere`. Si `{id}` correspond à une `Analyse` classique de la plateforme (jamais créée via `POST /api/ephemeral/analyses`), renvoie **404** — ne la supprime jamais.
- Renvoie **409** si des `dossier_ephemere` non supprimés référencent encore cette analyse (`dossier_ephemere.analyse_ephemere_id = {id}`) — le client doit d'abord supprimer les runs concernés (issue 05).
- Si aucune référence : supprime l'`Analyse` + la ligne `analyse_ephemere`. **Vérifier si une méthode de suppression d'`Analyse` existe déjà dans le code** (à l'inverse de `Dossier`, pas vérifié à ce stade) — si absente, l'ajouter dans cette issue (mêmes principes que l'issue 02 : cascade DB + nettoyage éventuel de fichiers liés).

## Critères d'acceptation

- [ ] `POST` crée bien une `Analyse` + `analyse_ephemere`, renvoie l'id dans tous les cas.
- [ ] `GET` renvoie 404 pour un id sans ligne `analyse_ephemere`, même si l'`Analyse` existe côté plateforme.
- [ ] `DELETE` renvoie 404 (analyse non éphémère), 409 (runs encore liés), ou 204 (succès).
- [ ] Tests couvrant les trois cas ci-dessus.
- [ ] Visibilité : accès scopé selon la section Authentification du design (issue 08 pour l'implémentation transverse, mais les endpoints doivent déjà appeler le bon contrôle d'accès).

## Fichiers concernés

- `backend/app/routers/ephemeral.py` (nouveau)
- `backend/app/routers/analyses.py` (réutilisation de la logique de création/lecture)
- `backend/app/repositories/analyse_repository.py` (réutilisation, non modifié)
- `backend/app/repositories/ephemeral_repository.py` (**nouveau**) : CRUD sur `AnalyseEphemere` — créer la ligne, la lire (avec jointure `Analyse`), la supprimer, vérifier l'existence de `dossier_ephemere` liés avant suppression. Mutualisé avec l'issue #23 qui y ajoute le CRUD `DossierEphemere`.
- `backend/app/main.py` (montage du router)

## Dépendances

Dépend de #20 (tables). Peut avancer en parallèle de #21, #23.
