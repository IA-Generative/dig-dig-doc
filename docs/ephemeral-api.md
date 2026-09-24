# API Ephemeral / On-Demand

## Contexte et objectif

On veut exposer une couche d'API permettant à un utilisateur (dev ou compte de service) de :

1. Récupérer la définition complète d'une analyse (agents, classification, entités).
2. Lancer le pipeline complet d'analyse (classification + extraction d'entités + agents) à la demande, sur un ensemble de documents, sans passer par le flux dossier standard de la plateforme.
3. Choisir, à chaque étape, si le résultat doit être conservé indéfiniment (`persist=true`, comportement actuel de la plateforme) ou être temporaire (`persist=false`, purgé automatiquement après un TTL).

La plateforme existante n'est pas modifiée : `Dossier`, `Analyse`, `ExecutionStep`, le pipeline Celery (`classify_dossier`, `extract_dossier_entities`, `run_agents`) et le stockage S3 restent tels quels. On ajoute une couche parallèle qui les réutilise.

## Principe du TTL

Le TTL ne démarre **pas** à la création de la ressource mais **à la fin de l'analyse** (`ended_at`). Tant que le run est en cours, `expires_at` reste `NULL` : on ne veut jamais purger un run en cours de traitement, même s'il reste en file d'attente longtemps.

```
expires_at = ended_at + ttl_hours   (posé au moment où le statut passe à un état terminal)
```

Le TTL est configurable par requête (`?ttl_hours=`) :

- **Défaut** : 24h si non fourni.
- **Maximum autorisé** : 2 ans (17 520h). Une valeur supérieure est rejetée (400) — au-delà, autant utiliser `persist=true`.

Pas de limite de taille ni de nombre de documents spécifique aux runs éphémères : les limites standard de la plateforme (upload, taille de fichier) s'appliquent telles quelles, sans restriction additionnelle.

## Modèle de données

Pas de duplication : `Analyse`, `Dossier`, `ExecutionStep`, `DossierDocument` et les résultats restent les tables existantes, utilisées telles quelles par le pipeline actuel. On ajoute seulement deux **tables d'association 1-1**, qui portent la métadonnée « ce record est éphémère » sans toucher au schéma ni au code métier existants.

### `analyse_ephemere`

Association avec `Analyse`.

| Champ | Type | Notes |
|---|---|---|
| `analyse_id` | uuid, PK + FK → `Analyse.id` | même id que l'analyse existante, renvoyé au client (`analyse_id`) |
| `persist` | bool, défaut `false` | si `true`, jamais purgée |
| `created_at` | timestamp | |
| `last_run_ended_at` | timestamp, nullable | mis à jour à chaque fin de run qui référence cette analyse |
| `expires_at` | timestamp, nullable | `NULL` si `persist=true` ou si jamais utilisée avant TTL ; sinon `last_run_ended_at + ttl_hours` |

Une `Analyse` **sans** ligne dans `analyse_ephemere` = analyse classique de la plateforme, comportement inchangé.

### `dossier_ephemere`

Association avec `Dossier` (le run).

| Champ | Type | Notes |
|---|---|---|
| `dossier_id` | uuid, PK + FK → `Dossier.id` | même id que le dossier existant, renvoyé au client (`run_id`) |
| `analyse_ephemere_id` | FK → `analyse_ephemere.analyse_id`, nullable | rempli seulement si l'analyse liée est elle-même éphémère |
| `persist` | bool, défaut `false` | indépendant du `persist` de l'analyse liée |
| `ttl_hours` | int, nullable | valeur effective utilisée pour ce run (`?ttl_hours=` ou défaut) |
| `expires_at` | timestamp, nullable | posé à `Dossier.ended_at + ttl_hours` dès passage à un statut terminal, si `persist=false` |

`DossierDocument`, `ExecutionStep` et les résultats/prédictions n'ont pas de TTL propre : ils sont supprimés en cascade avec leur `Dossier` (comportement déjà existant pour la suppression d'un dossier), donc purgés dès que `dossier_ephemere.expires_at` est dépassé.

Une `Dossier` **sans** ligne dans `dossier_ephemere` = dossier classique, comportement inchangé.

## Flux d'usage

### Flux A — en deux étapes (définir puis lancer)

1. `POST /api/ephemeral/analyses`
   Body : `agents`, `classification`, `entities`, `persist` (bool, défaut `false`).
   Réutilise la création `Analyse` existante, puis ajoute la ligne `analyse_ephemere` correspondante. Renvoie `{ "analyse_id": ... }` dans tous les cas (persistant ou non).

2. `POST /api/ephemeral/analyses/{analyse_id}/runs?ttl_hours=48`
   Multipart : fichiers + `persist` (bool, défaut `false`).
   Réutilise la création `Dossier` + upload de `DossierDocument` existante (même code que `dossiers.py`), lie ce dossier à l'analyse, ajoute la ligne `dossier_ephemere`, lance le pipeline complet (équivalent du `launch` existant, déclenché automatiquement). Renvoie `{ "run_id": ... }`.

### Flux B — en un seul appel (analyse déjà connue)

- `POST /api/ephemeral/runs?ttl_hours=48`
  Body : `analyse_id` + fichiers + `persist`.
  Équivalent à l'étape 2 du flux A sans repasser par l'étape 1. `analyse_id` peut être **soit** une analyse créée via `/api/ephemeral/analyses` (éphémère ou non), **soit** l'id d'une `Analyse` classique déjà existante sur la plateforme (jamais passée par ce flux) — cas d'usage confirmé : relancer une analyse déjà configurée sur des documents jetables, sans créer/modifier l'analyse elle-même. Dans ce second cas, `dossier_ephemere.analyse_ephemere_id` reste `NULL`.

### Lecture / arrêt / suppression

- `GET /api/ephemeral/analyses/{id}` — définition complète (agents/classification/entités)
- `GET /api/ephemeral/runs/{id}` — statut, et résultats une fois `terminé`
- `POST /api/ephemeral/runs/{id}/stop` — arrêt complet du run en cours (réutilise le `stop` existant de `dossiers.py:203`, coupe l'exécution Celery en cours), statut → `arrêté`. N'efface rien, juste stoppé, il reste consultable/purgeable normalement ensuite.
- `DELETE /api/ephemeral/runs/{id}` — arrête d'abord le run s'il est encore en cours (même effet que `stop`), puis supprime immédiatement le `Dossier`, ses `DossierDocument`, `ExecutionStep` et résultats (cascade existante) + la ligne `dossier_ephemere`. Suppression immédiate, sans attendre le TTL, sans toucher à l'analyse liée.
- `DELETE /api/ephemeral/analyses/{id}` — supprime immédiatement l'`Analyse` + la ligne `analyse_ephemere`. **Scope strict** : ne s'applique qu'aux analyses ayant une ligne `analyse_ephemere` (créées via `/api/ephemeral/analyses`). Si `{id}` correspond à une `Analyse` classique de la plateforme (jamais passée par ce flux), l'endpoint renvoie 404 — il ne la supprime jamais. Refusé (409) si des `dossier_ephemere` non supprimés y font encore référence, pour éviter une suppression en cascade surprise — le client doit d'abord `DELETE` les runs concernés.

### Comportement `persist` (validé)

- `persist` se règle indépendamment sur l'analyse et sur le run.
- Si l'analyse est `persist=true` mais le run est `persist=false` : l'analyse est conservée, seuls le run, ses documents et ses résultats sont purgés au TTL.
- Si l'analyse est `persist=false` et n'est jamais réutilisée par un run après sa création : elle expire selon son propre TTL (fallback sur `created_at + ttl_hours` si `last_run_ended_at` est `NULL`).

## Purge

Tâche Celery périodique, planifiée via **Celery beat** (réutilise l'infra Celery existante, pas de CronJob Helm à ajouter) :

1. À chaque passage d'un `Dossier` en statut terminal (`terminé`/`échec`/`arrêté`, y compris après un `stop` manuel), si une ligne `dossier_ephemere` existe et `persist=false` : poser `expires_at = ended_at + ttl_hours` — fait directement dans le code qui marque le run terminé (callback worker → `/api/internal/*`), pas en batch, pour être réactif. Même logique pour `analyse_ephemere.last_run_ended_at` / `expires_at` si le run référence une analyse éphémère.
2. Job périodique (ex. toutes les heures) : sélectionne les `dossier_ephemere` et `analyse_ephemere` avec `expires_at < now()` et `persist=false`, supprime le `Dossier`/`Analyse` correspondant (la cascade existante s'occupe de `DossierDocument`, `ExecutionStep`, résultats et fichiers S3 — même chemin de code qu'une suppression manuelle aujourd'hui).

## Authentification

Les endpoints `/api/ephemeral/*` acceptent **les deux** mécanismes d'auth existants :
- Token API (`app_tokens.py`) pour un usage programmatique / compte de service.
- Session Keycloak standard, pour un développeur qui teste depuis son compte.

**Visibilité :**

- Un compte Keycloak ne voit/ne peut agir (GET/stop/DELETE) que sur les analyses/runs éphémères auxquels il est associé — mêmes règles d'association que pour les analyses/dossiers classiques de la plateforme.
- Un token API (compte de service) voit/peut agir sur les ressources éphémères qu'il a créées.
- Pas de visibilité croisée entre comptes Keycloak et comptes de service en dehors de ces règles d'association/propriété.

## Découpage en issues

Suivi sur GitHub : [issues #20 à #29](https://github.com/IA-Generative/dig-dig-doc/issues?q=is%3Aissue+20..29). Détaillées individuellement dans `docs/issues/` tant qu'elles ne sont pas implémentées (le fichier est supprimé une fois le code mergé, l'issue GitHub reste la référence) :

1. [GitHub #20](https://github.com/IA-Generative/dig-dig-doc/issues/20) — création des tables d'association `analyse_ephemere` et `dossier_ephemere` (Alembic). ✅ implémenté (`backend/app/models/analyse_ephemere.py`, `dossier_ephemere.py`, migration `7f1e8bb1c9da`).
2. [`02-suppression-dossier.md`](issues/02-suppression-dossier.md) — (pré-requis, à construire from scratch) suppression complète d'un `Dossier` : DB (cascade déjà câblée) + nettoyage S3 (inexistant aujourd'hui).
3. [`03-endpoints-definition-analyse.md`](issues/03-endpoints-definition-analyse.md) — `POST/GET/DELETE /api/ephemeral/analyses`.
4. [`04-endpoints-run.md`](issues/04-endpoints-run.md) — `POST/GET /api/ephemeral/runs` (flux A + B).
5. [`05-stop-delete-run.md`](issues/05-stop-delete-run.md) — `POST .../stop` et `DELETE /api/ephemeral/runs/{id}`.
6. [`06-calcul-ttl.md`](issues/06-calcul-ttl.md) — logique `expires_at` sur fin de run, propagation vers `analyse_ephemere`.
7. [`07-tache-purge.md`](issues/07-tache-purge.md) — tâche Celery + planification Celery beat.
8. [`08-auth-visibilite.md`](issues/08-auth-visibilite.md) — double support token API / Keycloak + règles de visibilité.
9. [`09-documentation-openapi.md`](issues/09-documentation-openapi.md) — documentation OpenAPI du tag "Ephemeral".
10. [`10-mcp-server.md`](issues/10-mcp-server.md) — serveur MCP au-dessus de l'API éphémère, pour qu'un agent puisse l'appeler directement.

## Points tranchés

- TTL par défaut : 24h. TTL maximum : 2 ans.
- Pas de limite de taille/nombre de documents spécifique aux runs éphémères.
- Purge via Celery beat (déjà inclus dans le package `celery`, pas de CronJob Helm, pas de nouveau service).
- `persist` indépendant entre l'analyse et le run.
- Auth : token API et Keycloak tous les deux acceptés, scoping par association/propriété (cf. section Authentification).
- `DELETE /api/ephemeral/analyses/{id}` : scope strict aux analyses éphémères, 404 sinon.
- Flux B : `analyse_id` peut référencer une analyse éphémère ou une analyse classique de la plateforme.
- Pas de possibilité d'étendre un TTL déjà posé (pas de `PATCH .../ttl_hours`).

## Questions ouvertes / points à éclaircir

Aucun point bloquant restant à ce stade. Tout ce qui a été soulevé lors des passes de relecture a été tranché ci-dessus.
