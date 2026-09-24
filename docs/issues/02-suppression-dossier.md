# 02 — Suppression complète d'un `Dossier` (DB + S3)

Réf design : `docs/ephemeral-api.md`

## Contexte

Aucune suppression de `Dossier` n'existe aujourd'hui dans le code : pas d'endpoint `DELETE`, pas de méthode repository. C'est un prérequis bloquant pour l'API éphémère (`DELETE /api/ephemeral/runs/{id}` et la purge automatique en dépendent directement) — à construire de zéro, pas seulement à vérifier.

Le cascade DB est en revanche déjà bien câblé au niveau des modèles :
- `Dossier.execution_steps` → `cascade="all, delete-orphan"` + FK `ondelete="CASCADE"` (`backend/app/models/dossier.py:68-83`)
- `Dossier.documents` (`DossierDocument`) → même pattern (`backend/app/models/dossier.py:71-107`)
- `Dossier.conversations` → même pattern (`backend/app/models/dossier.py:74-76`)
- `ExecutionStep.logs` et `DossierDocument.pages` cascadent également en transitif.

Donc supprimer la ligne `Dossier` nettoiera correctement la base — mais rien ne le déclenche aujourd'hui, et **le nettoyage S3 des fichiers n'existe pas du tout**.

## Objectif

1. Méthode `delete_dossier(dossier_id)` dans `backend/app/repositories/dossier_repository.py` qui :
   - Récupère les `s3_key` de tous les `DossierDocument` du dossier (et de toute pièce jointe/résultat stockée sur S3 si applicable, ex. screenshots de pages).
   - Supprime les objets S3 correspondants via `S3Connector` (`backend/app/connectors.py:38-70`).
   - Supprime la ligne `Dossier` (le cascade DB s'occupe du reste).
   - Gère le cas où un objet S3 est déjà absent (ne doit pas faire échouer la suppression DB).
2. Point d'usage direct : cette méthode sera appelée par `DELETE /api/ephemeral/runs/{id}` (issue 05) et par le job de purge (issue 07). Pas besoin d'exposer un `DELETE /api/dossiers/{id}` public sur la plateforme standard dans cette issue, sauf si jugé utile en plus.

## Critères d'acceptation

- [ ] `delete_dossier` supprime bien les fichiers S3 associés (vérifié par test : upload → delete → objet absent du bucket).
- [ ] `delete_dossier` supprime bien la ligne `Dossier` et tout ce qui cascade (documents, execution_steps, conversations, pages, logs) en DB.
- [ ] Idempotent / robuste si un fichier S3 est déjà manquant (log un warning, ne bloque pas la suppression DB).
- [ ] Si un `Dossier` est encore `en_cours`, la suppression doit être refusée à ce niveau (repository) tant qu'il n'a pas été stoppé au préalable — la logique de stop-avant-delete se fait au niveau de l'endpoint (issue 05), le repository documente/vérifie juste la précondition.
- [ ] Tests unitaires sur `delete_dossier`.

## Fichiers concernés

- `backend/app/repositories/dossier_repository.py`
- `backend/app/connectors.py` (S3Connector, réutilisation)
- `backend/app/models/dossier.py` (vérifier les cascades citées ci-dessus)

## Dépendances

Aucune — peut être fait en parallèle de #20. Bloquant pour #24 et #26.
