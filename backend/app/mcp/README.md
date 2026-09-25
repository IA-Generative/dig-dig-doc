# Serveur MCP - dig-dig-doc éphémère

Ce dossier expose l'[API éphémère](../../../docs/ephemeral-api.md)
(`/api/ephemeral/*`) via [MCP](https://modelcontextprotocol.io/), pour
qu'un agent (Claude ou tout autre client MCP) puisse lancer une analyse à
la demande sans connaître le détail REST de l'API : créer une définition
d'analyse, lancer un run sur des fichiers, suivre son statut, récupérer le
résultat, puis le supprimer.

Ce README s'adresse à qui veut **connecter un client MCP** à ce serveur
(config, tools disponibles, exemple de scénario complet) - pas à
l'intégration du frontend React de la plateforme, qui n'a pas besoin de
MCP.

## Ce que c'est - et ce que ce n'est pas

- Le serveur tourne **dans le process du backend FastAPI** (pas un service
  séparé) : mêmes modèles/repositories, mêmes données que
  `/api/ephemeral/*`, appelés directement (pas d'aller-retour HTTP interne).
- Transport **Streamable HTTP**, monté sous `/mcp` sur le backend (donc
  `http://localhost:8000/mcp` en dev local, ou `<BACKEND_PUBLIC_URL>/mcp`
  en déploiement).
- Auth par **jeton API** (`POST /api/app-tokens`), présenté en
  `Authorization: Bearer <token>` - pas de session Keycloak côté MCP,
  cohérent avec un usage automatisé côté agent. Voir la section
  Authentification de `docs/ephemeral-api.md`.
- Toutes les ressources créées via MCP sont éphémères par défaut (TTL,
  purge automatique) - exactement le même comportement que l'API REST,
  simplement enveloppé en tools MCP.

## Installation / lancement

Rien à installer séparément : `mcp` est une dépendance du backend
(`backend/pyproject.toml`), et le serveur MCP démarre avec le backend lui-même :

```bash
docker compose up backend
# ou en dev sans Docker, depuis backend/ :
uv run uvicorn app.main:app --reload
```

Le endpoint est alors disponible sur `http://localhost:8000/mcp`.

## Obtenir un jeton API

```bash
curl -X POST http://localhost:8000/api/app-tokens \
  -H "Content-Type: application/json" \
  -b "<cookie de session Keycloak>" \
  -d '{"name": "mon-agent-mcp"}'
```

Le jeton n'est renvoyé qu'une fois, à la création (`token` dans la
réponse) - à conserver précieusement, il ne sera plus jamais réaffiché.

## Déclarer le serveur dans un client MCP

### Claude Code

```bash
claude mcp add --transport http dig-dig-doc-ephemeral http://localhost:8000/mcp \
  --header "Authorization: Bearer <votre-jeton-api>"
```

### Claude Desktop

Dans la configuration du client (`claude_desktop_config.json`) :

```json
{
  "mcpServers": {
    "dig-dig-doc-ephemeral": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer <votre-jeton-api>"
      }
    }
  }
}
```

## Tools exposés

Toutes les erreurs (404 introuvable/pas le créateur, 409 conflit, 400
`ttl_hours` hors bornes) sont renvoyées comme `{"error": str,
"status_code": int}` plutôt que comme une erreur de protocole MCP - à
vérifier dans la réponse de chaque tool.

### `create_ephemeral_analysis`

Crée une analyse (classification, extraction, agents) en un seul appel.

| Paramètre               | Type                | Description                                                          |
| ------------------------ | ------------------- | ---------------------------------------------------------------------- |
| `name`                   | `str`                | Requis.                                                                 |
| `description`             | `str`                | Défaut `""`.                                                            |
| `persist`                 | `bool`               | Défaut `false` (purgée au TTL). `true` = conservée indéfiniment.       |
| `classification_prompt`   | `str`                | Défaut `""`.                                                            |
| `labels`                  | `[{name, definition}]` | Défaut `[]`.                                                          |
| `extraction_prompt`       | `str`                | Défaut `""`.                                                            |
| `entities`                 | `[{name, definition, type}]` | `type` : `texte`\|`date`\|`nombre`\|`booléen`\|`identifiant`.    |
| `agents`                  | `[{name, prompt, tools, output, model}]` | Défaut `[]`.                                        |

Réponse : `{"analyse_id": "<uuid>"}`.

```json
{
  "name": "Analyse CNI + justificatif",
  "classification_prompt": "Classe le document (CNI, passeport, justificatif de domicile...)",
  "labels": [{ "name": "CNI", "definition": "Carte nationale d'identité" }],
  "extraction_prompt": "Extrait le nom, prénom et l'adresse",
  "entities": [{ "name": "nom", "definition": "Nom de famille", "type": "texte" }]
}
```

### `get_ephemeral_analysis`

`{"analyse_id": str}` → définition complète (classification, extraction,
agents, `persist`, `expires_at`).

### `delete_ephemeral_analysis`

`{"analyse_id": str}` → `{"deleted": true}`. Échoue (409, dans le champ
`error`) si des runs référencent encore cette analyse.

### `run_ephemeral_analysis`

Lance le pipeline complet (classification, extraction, agents) sur des
documents. Démarre immédiatement.

| Paramètre     | Type                                          | Description                                                          |
| -------------- | ---------------------------------------------- | ---------------------------------------------------------------------- |
| `analyse_id`   | `str`                                           | Une analyse créée via `create_ephemeral_analysis`, ou une analyse classique déjà existante sur la plateforme. |
| `files`        | `[{name, content_base64, mimetype}]`             | Contenu du fichier encodé en base64 (pas de multipart en MCP).        |
| `persist`      | `bool`                                           | Défaut `false`.                                                        |
| `ttl_hours`    | `int \| null`                                    | Défaut 24h, max 17520h (2 ans).                                       |

Réponse : `{"run_id": "<uuid>"}`.

### `get_ephemeral_run`

`{"run_id": str}` → statut (`en_attente`/`en_cours`/`terminé`/`arrêté`/`échec`)
et, une fois terminé, les résultats (classification, entités, sorties des
agents), plus `persist`/`ttl_hours`/`expires_at`.

### `stop_ephemeral_run`

`{"run_id": str}` → arrête un run en cours (no-op si déjà terminal). Pose
`expires_at` s'il ne l'était pas déjà.

### `delete_ephemeral_run`

`{"run_id": str}` → `{"deleted": true}`. Arrête d'abord le run si besoin,
puis supprime tout (documents, résultats, fichiers) immédiatement.

## Scénario complet

Équivalent MCP du scénario REST décrit dans `docs/ephemeral-api.md` :

1. `create_ephemeral_analysis` → récupère `analyse_id`.
2. `run_ephemeral_analysis` avec `analyse_id` + les fichiers (base64) →
   récupère `run_id`.
3. `get_ephemeral_run` en boucle (avec une pause entre chaque appel)
   jusqu'à ce que `status` soit `terminé`, `arrêté` ou `échec`.
4. Exploiter le résultat (`execution_steps[].output`,
   `documents[].pages[].predictions`).
5. `delete_ephemeral_run` (et éventuellement `delete_ephemeral_analysis`
   si elle n'est pas réutilisée) si le résultat n'a plus besoin d'être
   conservé - sinon, laisser faire la purge automatique au TTL.

## Serveur MCP helper (issue #50)

Un second serveur MCP, distinct du précédent, qui expose l'API **classique**
(`/api/analyses`, `/api/dossiers`) plutôt que l'éphémère : recherche/création
d'analyses et de dossiers **persistants** (pas de TTL), ajout de fichiers,
lancement du pipeline en asynchrone, consultation des résultats. Design
complet dans `docs/mcp-helper-agent-plan.md`.

### Ce que c'est - et ce que ce n'est pas

- Même process backend, même pattern d'appel direct aux fonctions des
  routers REST (pas d'aller-retour HTTP) que le serveur éphémère - voir
  `app/mcp/helper_server.py`.
- Transport Streamable HTTP, monté sous `/mcp/helper` (donc
  `http://localhost:8000/mcp/helper` en dev local, ou
  `<BACKEND_PUBLIC_URL>/mcp/helper` en déploiement) - **séparé** de `/mcp`
  (l'éphémère), pas une extension de celui-ci : deux cycles de vie
  différents (one-shot vs persistant/interactif).
- Même auth par jeton API (`POST /api/app-tokens`) que le serveur éphémère.
- **Persistant, pas de TTL** : contrairement à `/mcp`, les analyses et
  dossiers créés ici sont les mêmes ressources durables que celles gérées
  depuis l'UI - aucune purge automatique.
- Chaque tool accepte un `conversation_id` optionnel, obtenu via
  `create_agent_conversation` : s'il est fourni, l'appel (arguments +
  résultat) est journalisé dans `agent_messages`, pour l'audit ou pour
  qu'un futur agent conversationnel interne au produit (modal, à venir)
  retrouve l'historique de ce que l'agent a fait. Sans lui, le serveur
  reste stateless comme `/mcp` : le client porte son propre contexte.

### Déclarer le serveur dans un client MCP

#### Claude Code

```bash
claude mcp add --transport http dig-dig-doc-helper http://localhost:8000/mcp/helper \
  --header "Authorization: Bearer <votre-jeton-api>"
```

#### Claude Desktop

```json
{
  "mcpServers": {
    "dig-dig-doc-helper": {
      "url": "http://localhost:8000/mcp/helper",
      "headers": {
        "Authorization": "Bearer <votre-jeton-api>"
      }
    }
  }
}
```

### Tools exposés

Mêmes conventions que le serveur éphémère : les erreurs (404, 400...) sont
renvoyées comme `{"error": str, "status_code": int}` plutôt que comme une
erreur de protocole MCP.

| Tool | Endpoint REST équivalent | Description |
| ---- | ------------------------- | ------------ |
| `create_agent_conversation` | *(aucun)* | Crée une conversation pour journaliser les appels suivants. `{"conversation_id": "<uuid>"}`. |
| `list_analyses` | `GET /api/analyses` | Liste paginée des analyses persistantes. |
| `search_analyses` | `GET /api/analyses?q=` | Recherche par nom (insensible à la casse). |
| `get_analysis` | `GET /api/analyses/{id}` | Détail complet (labels, entités, agents, prompts). |
| `create_analysis` | `POST /api/analyses` | Crée une analyse (nom + description seulement - la classification/extraction/agents se configurent ensuite via la plateforme). |
| `create_dossier` | `POST /api/dossiers` | Crée un dossier lié à une analyse. |
| `add_dossier_files` | `POST /api/dossiers/{id}/documents` | Ajoute des fichiers (base64). |
| `list_dossiers` | `GET /api/dossiers` | Liste paginée des dossiers. |
| `get_dossier` | `GET /api/dossiers/{id}` | Détail d'un dossier (documents, statut, étapes, résultats). |
| `run_dossier` | `POST /api/dossiers/{id}/launch` | Lance le pipeline en asynchrone (classification, extraction, agents). |
| `get_dossier_results` | `GET /api/dossiers/{id}` | Alias de `get_dossier`, à appeler en boucle jusqu'à statut terminal. |

Tous les tools sauf `create_agent_conversation` acceptent en plus un
paramètre optionnel `conversation_id: str`.

### Scénario complet

1. `create_agent_conversation` (optionnel) → récupère `conversation_id`.
2. `search_analyses` ou `create_analysis` → récupère `analyse_id`.
3. `create_dossier` avec cet `analyse_id` → récupère `dossier_id`.
4. `add_dossier_files` avec les fichiers (base64).
5. `run_dossier` → démarre le pipeline, revient immédiatement.
6. `get_dossier_results` en boucle (avec une pause entre chaque appel)
   jusqu'à ce que `status` soit `termine`, `arrete` ou `echec`.
7. Exploiter le résultat (`execution_steps[].output`,
   `documents[].pages[].predictions`) - rien à supprimer, ces ressources
   sont persistantes.
