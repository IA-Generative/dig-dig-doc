# Plan d'implémentation : agent helper (MCP + chat interne)

Suivi d'implémentation de l'issue [#50](https://github.com/IA-Generative/dig-dig-doc/issues/50).
Branche : `feat/mcp-helper-agent` (créée depuis `main`, à jour au 2026-09-25).

Pas de TTL sur `agent_conversations`/`agent_messages` (conservées indéfiniment, comme les
dossiers classiques).

Convention de suivi : cocher au fur et à mesure de l'implémentation, dans cette branche.

## Découvertes clés de l'exploration du code (pourquoi ce découpage)

- `list_dossiers`/`create_dossier`/`get_dossier`/`launch_dossier` (`app/routers/dossiers.py`) et
  `list_analyses`/`create_analyse`/`get_analyse` (`app/routers/analyses.py`) **ne prennent pas
  d'identité utilisateur** (pas de `created_by`, ressources partagées plateforme) — contrairement
  aux ressources éphémères. Donc pas besoin de construire un `RequestContext` factice pour ces
  tools : on peut appeler les fonctions des routers directement avec juste `db`, exactement comme
  `app/mcp/server.py` le fait déjà pour l'éphémère.
- Lancer le pipeline = `POST /dossiers/{id}/launch` (pas `/run` comme nommé dans l'issue) →
  dispatch immédiat de 3 tâches Celery (`dispatch_classification`, `dispatch_entity_extraction`,
  `dispatch_agent_execution`) sur la file `agent_execution`, retour immédiat. Déjà asynchrone,
  rien à changer côté backend pour ça.
- Le worker (`worker/agent_execution`) est un **process séparé sans accès DB** : il parle au
  backend uniquement via `api_client.py` (HTTP, header `X-App-Token: INTERNAL_WORKER_TOKEN`) vers
  `/api/internal/*`. Le graphe de chat existant (`app/chat_graph.py` + `app/tasks/chat.py`) est le
  pattern de référence à répliquer pour `helper_graph.py`/`tasks/helper_chat.py` : mêmes briques
  (`EventCallback` streamant des `chat_events`, dépôt du message final avec sources via l'API
  interne).
- Conséquence sur "une seule implémentation, deux façades" (design de l'issue) : la vraie
  factorisation, c'est que **le serveur MCP et les nouveaux endpoints internes appellent tous les
  deux les mêmes fonctions de router** (`create_analyse`, `create_dossier`, `launch_dossier`, ...).
  Pas besoin d'une couche `agent_tools.py` séparée : le MCP server les appelle in-process (comme
  aujourd'hui), les endpoints internes les appellent aussi in-process (côté backend), et le worker
  les atteint via HTTP à travers ces endpoints internes.
- Seules les ressources *scopées utilisateur* (`agent_conversations`) ont besoin d'un identifiant
  d'acteur (`created_by`) — Keycloak `user_id` pour l'usage produit, `identity.id` (id du jeton
  API) pour l'usage MCP externe.

## Phase 1 — Modèle de données (backend) ✅ fait le 2026-09-25

- [x] `backend/app/models/agent_conversation.py` :
  - `AgentConversation` (`UUIDMixin`, `TimestampMixin`) : `created_by: str` (indexé), `title: str | None`.
  - `AgentMessageRole` (StrEnum) : `USER`, `ASSISTANT`, `TOOL_CALL`, `TOOL_RESULT`, `ERROR`.
  - `AgentMessage` (`UUIDMixin`, `TimestampMixin`) : `agent_conversation_id` (FK CASCADE), `role`,
    `content: str | None`, `tool_name: str | None`, `data: dict` (JSONB, défaut `{}`).
  - `AgentMessageSource` (`UUIDMixin`, `TimestampMixin`) : `message_id` (FK CASCADE),
    `dossier_id: UUID | None` (FK `dossiers.id`, `SET NULL`), `analyse_id: UUID | None` (FK
    `analyses.id`, `SET NULL`), `excerpt: str | None`.
- [x] `backend/app/models/agent_chat_event.py` : `AgentChatEventKind` (mêmes valeurs que
  `ChatEventKind`) + `AgentChatEvent` (`UUIDMixin`, `TimestampMixin`) : `agent_conversation_id`
  (FK CASCADE), `kind`, `data: dict` (JSONB) — copie quasi conforme de `chat_event.py`, FK vers
  `agent_conversations` au lieu de `conversations`.
- [x] Enregistré les nouveaux modèles dans `backend/app/models/__init__.py` (import + `__all__`,
  ordre alphabétique : `agent_chat_event`/`agent_conversation` passent avant `analyse` -
  "agent" < "analyse" alphabétiquement).
- [x] Migration `backend/migrations/versions/20260925_0849_d44d56718aa9_add_agent_conversations_agent_messages_.py`
  générée par autogenerate puis corrigée à la main : le `downgrade()` généré ne droppait pas les
  types Postgres `agent_message_role`/`agent_chat_event_kind` (juste les tables) - ajouté
  `sa.Enum(name=...).drop(op.get_bind(), checkfirst=True)` pour chacun, sur le modèle de
  `20260923_1400_d4e5f6a7b8c9_chat_events_table.py::downgrade` qui a le même besoin. Autogenerate
  avait aussi détecté un `chat_events.updated_at` à dropper (colonne présente en DB mais absente du
  modèle `ChatEvent`, dérive préexistante sans rapport avec cette issue) - retiré du diff pour ne
  pas mélanger les deux sujets.
- [x] Validé en local : `alembic upgrade head` (chaîne complète depuis une DB vide) puis
  `alembic downgrade -1` / `upgrade head` (roundtrip sur notre migration) passent proprement, et
  `uv run pytest` (backend) passe en entier (97 passed) une fois Postgres/Redis/rustfs démarrés
  (`docker compose up -d postgres redis rustfs`).
- ⚠️ Incident en cours de route : un premier roundtrip de validation (avant le fix du downgrade)
  a débordé sur une migration préexistante sans rapport (`2b084dba1bc8`, "add created_by to
  dossier_ephemere") et fait perdre le `created_by` de 36 lignes de test locales dans
  `dossier_ephemeres` (colonne `NOT NULL` sans défaut, redroppée puis impossible à
  ré-ajouter proprement). Résolu en réinitialisant le volume Postgres local
  (`docker compose down -v postgres` puis `up -d postgres`, confirmé avec l'utilisateur avant
  d'exécuter) - aucune donnée de prod concernée, uniquement la DB de dev locale.

## Phase 2 — Repository ✅ fait le 2026-09-25

- [x] `backend/app/repositories/agent_conversation_repository.py` (`AgentConversationRepository`),
  sur le modèle de la partie conversation de `dossier_repository.py` :
  - `create(created_by, title=None)`, `get(id)` (eager load messages + sources via
    `selectinload` + `populate_existing`, même pattern que `_conversation_query`),
  - `list_for_user_paginated(created_by, page, page_size)` — triée par `created_at desc` (pas de
    notion de "dernier message" façon dossier chat pour la V1 ; à revoir si besoin plus tard),
  - `delete(conversation)`,
  - `add_message(conversation, role, *, content=None, tool_name=None, data=None, sources=None)` —
    `sources` crée directement les `AgentMessageSource` (pas de méthode séparée, plus simple que
    le pattern dossier qui gère aussi des tables d'association pages/bboxes ici absentes),
  - `add_chat_event`/`list_chat_events`/`delete_chat_events`, identiques à leurs pendants
    `ChatEvent` de `dossier_repository.py`.
- [x] Vérifié `uv run ruff check` propre, puis exercé le repository de bout en bout contre la DB
  réelle (create → add_message ×3 avec tool_call/sources → get → list_for_user_paginated →
  add/list/delete chat_events → delete) via un script jetable (non committé) : tout se comporte
  comme attendu.
- [x] `uv run pytest` (backend) toujours à 97 passed après ce changement (le repository n'est pas
  encore branché à un router, donc pas de nouveaux tests d'intégration à ce stade - viendront en
  Phase 5 avec `agent_conversations` router).

## Phase 3 — API interne pour le worker (`/api/internal/agent/*`) ✅ fait le 2026-09-25

- [x] Ajouté le support `?q=` sur `GET /analyses` : `AnalyseRepository.list_paginated(..., q=None)`
  filtre par `Analyse.name.ilike(f"%{q}%")` (`app/repositories/analyse_repository.py`), branché
  sur le paramètre de requête du router existant (`app/routers/analyses.py::list_analyses`).
- [x] `backend/app/schemas/agent_conversation.py` créé en avance de la Phase 4 (nécessaire pour
  typer ces routes) : schémas produit (`AgentConversationOut`, `AgentMessageOut`, ...) et schémas
  internes (`InternalAgentConversationOut`, `InternalAgentMessageIn`, ...) dans le même fichier.
- [x] `backend/app/routers/internal_agent.py` : **deux** routers séparés (pas un seul avec des
  chemins concaténés, plus lisible) :
  - `agent_conversations_router` (préfixe `/internal/agent-conversations`) : `GET /{id}` (ne
    renvoie que les messages `user`/`assistant`, filtrés en Python - les `tool_call`/`tool_result`
    déjà journalisés ne sont pas utiles au graphe pour reconstruire son contexte),
    `POST /{id}/chat-events`, `POST /{id}/messages` (dépose la réponse assistant + sources).
  - `router` (préfixe `/internal/agent`) : `list_agent_analyses`/`get_agent_analyse`/
    `create_agent_analyse` et `list_agent_dossiers`/`get_agent_dossier`/`create_agent_dossier`/
    `launch_agent_dossier` sont des **wrappers d'une ligne** qui appellent directement les
    fonctions de `app/routers/analyses.py`/`app/routers/dossiers.py` (confirmé : pas d'identité
    requise, donc pas de `RequestContext` à construire) - même stratégie que `app/mcp/server.py`
    pour l'éphémère. `add_agent_dossier_files` est la seule route réécrite (pas un simple wrapper)
    car l'endpoint classique attend des `UploadFile` (multipart) ; elle décode du base64 et
    réutilise `DossierRepository.add_documents` directement, sur le modèle de
    `app/routers/ephemeral.py::_create_run`.
  - Les deux routers sont protégés par `Depends(verify_app_token)` (même mécanisme que
    `/api/internal/*`), montés dans `app/main.py` juste après `internal_router`.
- [x] Validé avec un script jetable (httpx.AsyncClient + ASGITransport, un seul event loop pour
  éviter le piège documenté dans `tests/conftest.py::client`) : tout le cycle
  conversation (get 404 → seed via repository → get → chat-event → message assistant → get) puis
  tools (create/search/get analyse → create/list/get dossier → upload de fichier en base64 →
  launch) répond `200`/`201` comme attendu, et un appel sans `X-App-Token` répond `401`/`422`.
- [x] `uv run pytest` (backend) toujours à 97 passed.

## Phase 4 — Schémas Pydantic ✅ fait en Phase 3 (2026-09-25)

- [x] `backend/app/schemas/agent_conversation.py` créé pendant la Phase 3 (nécessaire pour typer
  les routes internes) : `AgentConversationOut`, `AgentConversationSummaryOut` (avec
  `from_conversation()`, pour la liste sidebar), `AgentMessageOut`, `AgentMessageSourceOut`,
  `AgentChatEventOut`/`AgentChatEventIn`, `AgentMessageIn` (body de `POST .../messages` côté REST
  produit, restent à consommer en Phase 5) + les schémas internes utilisés en Phase 3.

## Phase 5 — API REST produit (`backend/app/routers/agent_conversations.py`, auth Keycloak) ✅ fait le 2026-09-25

- [x] `dispatch_helper_chat_response(conversation_id)` ajouté à `app/celery_client.py`, sur le
  modèle de `dispatch_chat_response` mais sans `dossier_id` (queue `agent_execution`, tâche
  `app.tasks.run_helper_chat` - à créer en Phase 7).
- [x] `GET /api/agent-conversations` — liste paginée de l'utilisateur courant (`user.user_id`),
  vue `AgentConversationSummaryOut` (titre, dernier message, `created_at`).
- [x] `POST /api/agent-conversations` — crée une conversation vide (`title=None`).
- [x] `GET /api/agent-conversations/{id}` — 404 si la conversation n'existe pas ou n'appartient
  pas à l'utilisateur courant (`_get_owned_or_404`, vérifie `created_by == user.user_id`).
- [x] `DELETE /api/agent-conversations/{id}` — 204, même contrôle de propriété.
- [x] `POST /api/agent-conversations/{id}/messages` — dépose le message `user`, **génère le titre
  au premier message** si absent (troncage à 60 caractères, `_truncate_title` - décision "points
  ouverts" tranchée : troncage simple pour la V1, pas d'appel LLM dédié), nettoie les
  `agent_chat_events` de l'exécution précédente, puis dispatch
  `dispatch_helper_chat_response`.
- [x] `GET /api/agent-conversations/{id}/stream` — SSE des `agent_chat_events`, copie quasi
  conforme de `dossiers.py::stream_chat_events`/`_chat_events` (polling 500ms, s'arrête sur
  `done`/`error`, revérifie la propriété à chaque poll).
- [x] Router monté dans `app/main.py` (tag `"Agent"` ajouté aux `openapi_tags`).
- [x] Validé avec un script jetable en async pur (httpx.AsyncClient + ASGITransport, un seul event
  loop - **piège rencontré** : mélanger `TestClient` (sync, son propre event loop via portail
  anyio) avec un `asyncio.run()` séparé pour seeder la DB casse le pool de connexions asyncpg
  partagé, `RuntimeError: ... attached to a different loop` ; la solution qui marche à tous les
  coups est de rester dans un seul `asyncio.run()` du début à la fin, y compris pour le seeding
  direct via le repository) : cycle complet liste/création/get/post-message (titre auto-généré,
  dispatch appelé) → générateur SSE testé directement (seed d'un event `done`, vérifie qu'il
  termine au lieu de boucler indéfiniment - le tester via une vraie requête HTTP streamée bloque
  le script, cf. incident ci-dessous) → isolation entre utilisateurs (404 + liste vide pour un
  autre `user_id`) → delete → 404 après.
- ⚠️ Incident mineur (sans conséquence, corrigé dans le script de validation lui-même, pas dans le
  code) : un premier essai de tester le flux SSE via une vraie requête HTTP streamée
  (`client.stream(...)`) a fait tourner le script indéfiniment (timeout 120s, tué manuellement) -
  attendu, le générateur ne se termine que sur un événement `done`/`error` qu'aucun worker ne
  dépose dans ce smoke test. Remplacé par un appel direct au générateur `_agent_chat_events` avec
  un événement `done` seedé à la main.
- [x] `uv run pytest` (backend) toujours à 97 passed.

## Phase 6 — Serveur MCP helper (`backend/app/mcp/helper_server.py`)

- [ ] Nouveau `MCPServer` (nom `dig-dig-doc-helper`), monté sous `/mcp/helper` dans `app/main.py`
  (même `BearerTokenAuthMiddleware` que `/mcp`, cf. `app.mount("/mcp", ...)` existant).
- [ ] Tools, appelant directement les fonctions de router (comme `app/mcp/server.py` le fait pour
  l'éphémère, avec `async with async_session_factory() as db`) :
  `list_analyses`, `search_analyses`, `get_analysis`, `create_analysis`, `create_dossier`,
  `add_dossier_files`, `list_dossiers`, `get_dossier`, `run_dossier` (→ `launch_dossier`),
  `get_dossier_results` (→ `get_dossier`).
- [ ] `conversation_id` optionnel sur chaque tool (décision de l'issue) : si fourni, journalise un
  `agent_message` `tool_call`/`tool_result` via `AgentConversationRepository`, scopé par
  `identity.id` (`get_current_identity()`, comme `app/mcp/server.py`).
- [ ] Pas de tool dédié `start_agent_conversation` côté MCP (design final de l'issue) — un client
  externe qui veut journaliser crée la conversation via l'API interne/produit au préalable, ou on
  ajoute un tool `create_agent_conversation` minimal si ça s'avère plus pratique à l'usage (à
  garder en tête, non bloquant).
- [ ] Tests `backend/tests/test_mcp_helper.py`, sur le modèle de `test_mcp.py`.

## Phase 7 — Worker (`worker/agent_execution`)

- [ ] `app/helper_tools.py` : classe `HelperTools` (sur le modèle de `app/tools.py`), méthodes
  qui appellent `api_client` vers `/internal/agent/*` : `search_analyses`, `get_analysis`,
  `create_analysis`, `create_dossier`, `add_dossier_files`, `list_dossiers`, `get_dossier`,
  `launch_dossier`. Chaque tool qui produit un dossier/analyse enregistre une
  `ConsultedSource`-like (`dossier_id`/`analyse_id`) pour peupler `agent_message_sources`.
- [ ] `app/api_client.py` : ajouter les fonctions HTTP correspondantes
  (`get_agent_conversation`, `add_agent_chat_event`, `deposit_agent_assistant_message`,
  `list_analyses`, `search_analyses`, `get_analysis`, `create_analysis`, `create_dossier`,
  `add_dossier_files`, `list_dossiers`, `get_dossier`, `launch_dossier`).
- [ ] `app/helper_graph.py` : graphe LangGraph ReAct, sur le modèle de `app/chat_graph.py`
  (`EventCallback`, boucle agent→tools→agent, prompt système décrivant les capacités de l'agent
  helper).
- [ ] `app/tasks/helper_chat.py` : tâche Celery `app.tasks.run_helper_chat(conversation_id)`, sur
  le modèle exact de `app/tasks/chat.py::run_chat` (charge historique, exécute le graphe avec
  streaming, dépose la réponse + sources, émet `done`/`error`).
- [ ] Enregistrer la tâche (import dans le point d'entrée Celery du worker, cf. comment
  `app.tasks.run_chat` est déclaré/découvert).
- [ ] Tests worker (si un dossier de tests existe déjà pour `chat.py`/`chat_graph.py`, suivre le
  même emplacement).

## Phase 8 — Frontend

- [ ] Extraire l'UI de chat de `frontend/src/pages/DossierDetailPage.vue` (section
  `chat-window`, ~L271-360, + logique `chatEvents`/`messages`/`isChatRunning`/scroll) en composant
  réutilisable `frontend/src/components/ChatWindow.vue` (props : liste de messages génériques,
  slot pour les actions spécifiques dossier comme le feedback thumbs up/down) + composable
  `frontend/src/composables/useChatStream.ts` (SSE générique, actuellement inline dans la page).
  Rebrancher `DossierDetailPage.vue` dessus sans changement de comportement.
- [ ] `frontend/src/types/agentConversation.ts` : types `AgentConversation`,
  `AgentConversationSummary`, `AgentMessage`, `AgentMessageSource`.
- [ ] `frontend/src/composables/useAgentConversations.ts` (liste/CRUD, sur le modèle de
  `useConversations.ts`/`useMyConversations.ts`).
- [ ] `frontend/src/components/HelperAgentModal.vue` : mini-sidebar (liste des
  `agent_conversations` via `useAgentConversations`) + `ChatWindow.vue` branché sur
  `/api/agent-conversations/*`. Une source `dossier_id` dans un message → lien cliquable
  `router.push({ path: '/dossiers/' + dossierId })`.
- [ ] Bouton d'ouverture dans `frontend/src/components/UserMenu.vue` (à côté des entrées
  existantes `goProfile`/`openChangelog`, même pattern `showX = ref(false)` + `<HelperAgentModal
  v-if="showHelperAgent" />`).
- [ ] Indicateur "pipeline en cours" pendant qu'un `launch_dossier` tourne côté agent (réutiliser
  le statut `DossierStatus` déjà affiché sur `DossierDetailPage.vue`).

## Phase 9 — Documentation

- [ ] `backend/app/mcp/README.md` : nouvelle section "Serveur MCP helper" (config client, tools,
  scénario complet), sur le modèle de la section éphémère existante.
- [ ] Mettre à jour les critères d'acceptation cochés sur l'issue #50 au fur et à mesure.

## Points laissés ouverts (à trancher en cours de route, non bloquants)

- ~~Génération du `title` de conversation~~ tranché en Phase 5 : troncage du premier message à 60
  caractères (`agent_conversations.py::_truncate_title`), pas d'appel LLM dédié pour la V1.
- Une seule conversation active à la fois dans la modal, ou plusieurs onglets — commencer par une
  seule (comme la modal `InfoModal`), itérer si besoin.
