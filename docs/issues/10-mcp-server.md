# 10 — Serveur MCP au-dessus de l'API éphémère

Réf design : `docs/ephemeral-api.md`

## Contexte

Une fois l'API `/api/ephemeral/*` en place, l'exposer aussi via un serveur MCP (Model Context Protocol) permettrait à un agent (Claude ou autre client MCP) d'orchestrer directement une analyse à la demande : récupérer une définition d'analyse, lancer un run sur des documents fournis par l'agent, suivre son statut, récupérer le résultat, puis le supprimer — sans que l'agent ait à connaître le détail REST de l'API.

C'est une extension, pas un prérequis : elle ne modifie rien à l'API HTTP elle-même, elle l'enveloppe.

## Objectif

Un serveur MCP (nouveau service ou module, à héberger à côté du backend) exposant des tools MCP correspondant 1-1 aux endpoints `/api/ephemeral/*` :

- `list_ephemeral_config` → équivalent `GET /api/ephemeral/analyses/{id}` / config globale (classifications, entités, agents disponibles).
- `create_ephemeral_analysis` → `POST /api/ephemeral/analyses`.
- `run_ephemeral_analysis` → `POST /api/ephemeral/analyses/{id}/runs` ou `POST /api/ephemeral/runs` (flux A/B), avec upload des fichiers fournis par le client MCP.
- `get_ephemeral_run` → `GET /api/ephemeral/runs/{id}` (statut + résultats).
- `stop_ephemeral_run` → `POST /api/ephemeral/runs/{id}/stop`.
- `delete_ephemeral_run` / `delete_ephemeral_analysis` → `DELETE` correspondants.

## Points à trancher avant implémentation

- Authentification du serveur MCP vis-à-vis du backend : token API dédié (`app_tokens.py`) plutôt que Keycloak, cohérent avec un usage automatisé côté agent.
- Où héberger ce serveur : processus séparé (Python, `mcp` SDK) appelant l'API HTTP existante, ou intégré directement dans le backend FastAPI (ex. via une lib exposant des routes FastAPI comme tools MCP) — à comparer.
- Gestion des fichiers : un client MCP transmet des fichiers différemment d'un upload HTTP classique (selon le transport MCP utilisé) — à valider selon le SDK MCP retenu.
- Faut-il streamer le statut d'avancement du run (équivalent SSE `GET .../stream`) vers l'agent, ou seulement du polling via `get_ephemeral_run` ? Proposition : polling dans un premier temps, streaming en amélioration ultérieure si besoin.

## Critères d'acceptation

- [ ] Serveur MCP exposant au minimum les 6 tools listés ci-dessus.
- [ ] Auth par token API, pas de session Keycloak côté MCP.
- [ ] Un agent MCP peut réaliser le cycle complet : lister la config → créer/référencer une analyse → lancer un run avec des fichiers → suivre le statut → récupérer le résultat → supprimer.
- [ ] `README.md` dédié au serveur MCP (dans son répertoire, ex. `mcp/README.md`), destiné à qui veut brancher un agent/client MCP dessus (pas au code du frontend React de la plateforme) :
  - Ce qu'est ce serveur et à quoi il sert (résumé du contexte ci-dessus).
  - Comment l'installer/lancer en local (dépendances, variables d'environnement, notamment le token API à fournir).
  - Comment le déclarer dans un client MCP (exemple de config JSON pour Claude Desktop et Claude Code - transport stdio ou HTTP selon ce qui est retenu).
  - Liste des tools exposés, avec pour chacun : son objectif, ses paramètres, un exemple d'appel et de réponse.
  - Un exemple de cycle complet (créer une analyse → lancer un run avec des fichiers → suivre le statut → récupérer le résultat → supprimer), équivalent MCP du scénario déjà documenté pour l'API REST dans `docs/ephemeral-api.md`.
- [ ] Lien vers ce `README.md` ajouté depuis `docs/ephemeral-api.md` et depuis le `README.md` racine du repo (section listant les services/composants du projet, si une telle section existe déjà).

## Fichiers concernés

- Nouveau module/service MCP (emplacement à définir, ex. `backend/mcp/` ou service séparé) + son `README.md`
- `backend/app/routers/ephemeral.py` (consommé via HTTP, pas modifié)
- `backend/app/routers/app_tokens.py` (auth du serveur MCP)
- `README.md` racine (lien vers la doc MCP, si pertinent)

## Dépendances

Dépend de #22, #23, #24, #27 (l'ensemble de l'API éphémère doit être stable et fonctionnelle avant de l'envelopper en MCP). Non bloquant pour la release initiale de l'API — peut être fait dans un second temps.
