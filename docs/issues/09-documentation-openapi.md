# 09 — Documentation OpenAPI du tag "Ephemeral"

Réf design : `docs/ephemeral-api.md`

## Contexte

Dernière étape : s'assurer que le nouveau router est correctement documenté dans le schéma OpenAPI exposé par le backend (`/api/openapi.json`), au même niveau de qualité que les tags existants ("Analyses", "Dossiers", ...).

## Objectif

- Tag "Ephemeral" (ou "Ephémère") sur tous les endpoints de `backend/app/routers/ephemeral.py`, avec description courte du rôle de chaque endpoint (cf. `docs/ephemeral-api.md` pour le contenu).
- Schémas Pydantic clairs pour les payloads d'entrée/sortie (`AnalyseEphemereCreate`, `RunEphemereCreate`, `RunEphemereOut`, etc.), avec exemples (`example`/`examples` dans les `Field`/`Config`).
- Documenter explicitement dans la description des endpoints :
  - Le comportement du TTL (départ au `ended_at`, pas à la création).
  - Le comportement `persist` (indépendant analyse/run).
  - Les codes d'erreur spécifiques (404 scope strict sur `DELETE analyses`, 409 si runs encore liés, 400 si `ttl_hours` hors bornes).
- Vérifier le rendu dans Swagger UI / Redoc (si exposé) une fois les endpoints en place.

## Critères d'acceptation

- [ ] Tous les endpoints `/api/ephemeral/*` apparaissent sous un tag dédié dans `/api/openapi.json`.
- [ ] Chaque endpoint a une description, des exemples de payload, et les codes de réponse documentés.
- [ ] Relecture du rendu Swagger/Redoc par quelqu'un n'ayant pas suivi le design (test de clarté).

## Fichiers concernés

- `backend/app/routers/ephemeral.py`
- `backend/app/main.py` (config des tags OpenAPI si centralisée)

## Dépendances

Dépend de #22, #23, #24, #25, #26, #27 — à faire en dernier, une fois tous les endpoints stabilisés.
