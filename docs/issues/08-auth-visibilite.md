# 08 — Auth et visibilité sur le router `ephemeral`

Réf design : `docs/ephemeral-api.md`

## Contexte

Les endpoints `/api/ephemeral/*` doivent accepter les deux mécanismes d'auth existants de la plateforme, avec des règles de visibilité différentes selon le mécanisme utilisé.

## Objectif

1. **Double support d'authentification** sur le router `ephemeral` :
   - Token API externe (`backend/app/routers/app_tokens.py`), pour un usage programmatique / compte de service.
   - Session Keycloak standard (`backend/app/core/security/`), pour un développeur qui teste depuis son propre compte.
2. **Règles de visibilité** (GET / stop / DELETE) :
   - Un compte Keycloak ne voit et n'agit que sur les analyses/runs éphémères auxquels il est associé — mêmes règles d'association que pour les analyses/dossiers classiques de la plateforme (à identifier précisément dans le code existant, probablement au niveau dossier/analyse owner ou permissions Keycloak).
   - Un token API (compte de service) voit et agit sur les ressources éphémères qu'il a créées.
   - Pas de visibilité croisée entre comptes Keycloak et comptes de service en dehors de ces règles.
3. Appliquer ces règles de façon cohérente sur tous les endpoints du router (`POST`/`GET`/`DELETE`/`stop`, issues 03/04/05).

## Critères d'acceptation

- [ ] Les deux mécanismes d'auth fonctionnent sur tous les endpoints `/api/ephemeral/*`.
- [ ] Un compte Keycloak non associé à une analyse/run éphémère reçoit 403/404 (à trancher lequel, cohérent avec le reste de l'API) en essayant d'y accéder.
- [ ] Un token API ne voit que les ressources qu'il a lui-même créées.
- [ ] Tests couvrant : accès autorisé Keycloak, accès refusé Keycloak (autre utilisateur), accès autorisé token, accès refusé token (autre token).

## Fichiers concernés

- `backend/app/routers/ephemeral.py`
- `backend/app/routers/app_tokens.py`
- `backend/app/core/security/` (dépendances FastAPI d'auth existantes)

## Dépendances

Dépend de #22, #23, #24 (s'applique sur leurs endpoints). Peut être développé en parallèle et intégré au fur et à mesure.
