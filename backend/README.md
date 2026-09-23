# dig-dig-doc backend

BFF (Backend For Frontend) FastAPI. Configuration entièrement par variables
d'environnement (pydantic-settings). En dev via `docker compose`, ces
variables sont injectées par `docker-compose.yaml` (racine du repo), qui
lui-même lit `.env` à la racine pour les `${VARIABLE}` qu'il référence -
voir `.env.example` à la racine du repo et la section _Configuration_ du
[README principal](../README.md).

## Variables d'environnement

### Base de données (`DatabaseSettings`)

| Variable       | Défaut                                                              | Description                    |
| -------------- | ------------------------------------------------------------------- | ------------------------------ |
| `DATABASE_URL` | `postgresql+asyncpg://digdigdoc:digdigdoc@localhost:5432/digdigdoc` | URL Postgres (driver asyncpg). |

### Redis (`RedisSettings`)

| Variable    | Défaut                     | Description                                         |
| ----------- | -------------------------- | --------------------------------------------------- |
| `REDIS_URL` | `redis://localhost:6379/0` | Broker Celery + cache (ex : liste des modèles LLM). |

### Stockage S3 / RustFS (`StorageSettings`)

| Variable          | Défaut                  | Description                                       |
| ----------------- | ----------------------- | ------------------------------------------------- |
| `S3_ENDPOINT_URL` | `http://localhost:9000` | RustFS en local/dev, un vrai endpoint S3 en prod. |
| `S3_ACCESS_KEY`   | `rustfsadmin`           |                                                   |
| `S3_SECRET_KEY`   | `rustfsadmin`           |                                                   |
| `S3_BUCKET`       | `dig-dig-doc`           |                                                   |
| `S3_REGION`       | `us-east-1`             |                                                   |

### Keycloak / sessions (`KeycloakSettings`)

| Variable                  | Défaut                               | Description                                                          |
| ------------------------- | ------------------------------------ | -------------------------------------------------------------------- |
| `KEYCLOAK_URL`            | `http://localhost:8080`              | URL backend → Keycloak (nom de service Docker en dev).               |
| `KEYCLOAK_PUBLIC_URL`     | _(vide, retombe sur `KEYCLOAK_URL`)_ | URL Keycloak côté navigateur si différente (reverse proxy).          |
| `KEYCLOAK_REALM`          | `dig-dig-doc`                        |                                                                      |
| `KEYCLOAK_CLIENT_ID`      | `dig-dig-doc-backend`                |                                                                      |
| `KEYCLOAK_CLIENT_SECRET`  | _(vide)_                             | À définir en prod.                                                   |
| `BACKEND_PUBLIC_URL`      | `http://localhost:8000`              | Sert à construire le `redirect_uri` OAuth2 enregistré côté Keycloak. |
| `FRONTEND_URL`            | `http://localhost:5173`              | Où rediriger après login/logout ; aussi utilisé pour CORS.           |
| `SESSION_COOKIE_NAME`     | `digdigdoc_session`                  |                                                                      |
| `SESSION_COOKIE_SECURE`   | `true`                               |                                                                      |
| `SESSION_COOKIE_SAMESITE` | `lax`                                |                                                                      |
| `SESSION_TTL_SECONDS`     | `604800` (7 jours)                   |                                                                      |

### Partage & jetons internes (`SharingSettings`)

| Variable                  | Défaut                               | Description                                                                             |
| ------------------------- | ------------------------------------ | --------------------------------------------------------------------------------------- |
| `SHARE_SECRET_KEY`        | `dev-only-share-secret-not-for-prod` | Clé HMAC des liens de partage d'analyse par email. À changer en prod.                   |
| `SHARE_DEFAULT_TTL_HOURS` | `168` (7 jours)                      |                                                                                         |
| `INTERNAL_WORKER_TOKEN`   | `dev-only-worker-token-not-for-prod` | Jeton statique de bootstrap pour les workers Celery (`X-App-Token`). À changer en prod. |

### Modèles LLM (`LlmSettings`)

| Variable                        | Défaut   | Description                                                 |
| ------------------------------- | -------- | ----------------------------------------------------------- |
| `OPENAI_API_KEY`                | _(vide)_ | Clé du hub LLM (compatible API OpenAI).                     |
| `OPENAI_API_BASE_URL`           | _(vide)_ | URL de base du hub (ex : `https://mon-hub.example.com/v1`). |
| `CHAT_MODELS_CACHE_TTL_SECONDS` | `3600`   | Durée de mise en cache Redis de la liste des modèles.       |

`GET /api/models` utilise la librairie [`openai`](https://pypi.org/project/openai/)
(client `AsyncOpenAI`, ajouté aux dépendances du projet) pour interroger ce
hub : `models.list()` énumère tout ce qu'il sert (chat, embeddings, etc.),
puis chaque modèle candidat est testé avec un appel `chat.completions.create`
minimal pour ne garder que ceux qui savent réellement faire du chat. Le
résultat est mis en cache dans Redis (`CHAT_MODELS_CACHE_TTL_SECONDS`) pour
éviter de re-sonder le hub à chaque appel.

Sans `OPENAI_API_KEY`/`OPENAI_API_BASE_URL`, la route répond `503 Service
Unavailable` plutôt que de parler à un hub public par défaut - le frontend
affiche alors un sélecteur de modèle vide au lieu de planter.

Ces deux variables sont aussi ce qui alimente les sélecteurs de modèle
d'une conversation et d'un agent (`model` stocké sur `Conversation`/`Agent`,
voir `PUT .../conversations/{id}/model` et `PUT .../agents/{id}/model`).

## Configuration locale

Depuis la racine du repo :

```bash
cp .env.example .env
```

`.env.example` est versionné (valeurs par défaut/placeholders, aucun
secret réel). `.env` ne l'est jamais (voir `.gitignore`) : c'est là que
vont les vraies clés/URLs (LLM hub, secrets Keycloak/partage en prod...).
`docker compose up` le lit automatiquement.
