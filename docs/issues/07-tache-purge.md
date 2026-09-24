# 07 — Tâche de purge périodique (Celery beat)

Réf design : `docs/ephemeral-api.md`

## Contexte

Une fois `expires_at` posé (issue 06), il faut une tâche périodique qui supprime effectivement les ressources expirées. Planification via **Celery beat**, inclus dans le package `celery` déjà utilisé par le projet (`backend/app/celery_client.py`) — pas de CronJob Kubernetes/Helm à ajouter, pas de nouveau service à provisionner.

## Objectif

1. Nouvelle tâche Celery (ex. `purge_expired_ephemeral`), planifiée via `beat_schedule` (ex. toutes les heures — fréquence à ajuster selon le TTL minimum réel observé).
2. Logique de la tâche :
   - Sélectionne tous les `dossier_ephemere` avec `expires_at < now()` et `persist=false`.
   - Pour chacun : appelle `delete_dossier` (issue 02) — supprime le `Dossier` (cascade DB) + fichiers S3 + la ligne `dossier_ephemere` elle-même.
   - Sélectionne tous les `analyse_ephemere` avec `expires_at < now()` et `persist=false`, **et sans `dossier_ephemere` restant y faisant référence** (cohérent avec la contrainte 409 du `DELETE` manuel, issue 03 — la purge automatique ne doit pas violer la même règle).
   - Pour chacune : supprime l'`Analyse` + la ligne `analyse_ephemere`.
3. Traiter les suppressions par lot (batch), avec logs (nombre de runs/analyses purgés, erreurs éventuelles) pour observabilité.
4. Vérifier si un service `celery beat` est déjà déployé (worker dédié ou flag sur un worker existant) — sinon, l'ajouter à la configuration de déploiement (`docker-compose.yaml`, Helm) en plus de la tâche elle-même.

## Critères d'acceptation

- [ ] Tâche Celery créée, planifiée via `beat_schedule`.
- [ ] Suppression cohérente : un run expiré est bien supprimé (DB + S3), une analyse expirée sans run restant est bien supprimée.
- [ ] Une analyse expirée mais encore référencée par un `dossier_ephemere` non supprimé n'est **pas** purgée (attend que ses runs soient purgés en premier).
- [ ] Service `celery beat` bien déployé en environnement de test/prod (vérifié, pas supposé).
- [ ] Logs/métriques minimales sur chaque exécution de la purge.
- [ ] Test d'intégration : créer un run avec un TTL très court, attendre, vérifier la suppression effective après exécution de la tâche.

## Fichiers concernés

- `backend/app/tasks.py` (ou équivalent, nouvelle tâche)
- `backend/app/celery_client.py` (configuration beat schedule)
- `backend/app/repositories/dossier_repository.py`, `analyse_repository.py`
- `docker-compose.yaml` / Helm (si un service beat doit être ajouté)

## Dépendances

Dépend de #20, #21, #25.
