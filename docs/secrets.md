# Secrets Kubernetes — dig-dig-doc

Les secrets sont gérés via **HashiCorp Vault** (Vault Static Secrets via VSO) et référencés
dans `digdigdoc/values/common-values.yaml` sous `extraObjects`.

Chaque secret ci-dessous correspond à un **chemin Vault** (`mirai` mount, kv-v2) et à un
**Secret Kubernetes** créé automatiquement par le Vault Secrets Operator.

---

## Tableau récapitulatif

| Secret K8s                | Chemin Vault (`exploration/`)       | Type K8s                    | Utilisé par                          |
| ------------------------- | ------------------------------ | --------------------------- | ------------------------------------ |
| `digdigdoc-s3`            | `digdigdoc-s3`                 | Opaque                      | backend, worker_document, worker_agent |
| `digdigdoc-keycloak`      | `digdigdoc-keycloak`           | Opaque                      | backend                               |
| `digdigdoc-openai`        | `digdigdoc-openai`             | Opaque                      | backend                               |
| `digdigdoc-worker`        | `digdigdoc-worker`             | Opaque                      | backend, worker_document, worker_agent |
| `digdigdoc-redis`         | `digdigdoc-redis`              | Opaque                      | backend, worker_document, worker_agent, redis sub-chart, KEDA |
| `digdigdoc-meilisearch`   | `digdigdoc-meilisearch`        | Opaque                      | backend (envFrom)                     |
| `digdigdoc-db-superuser`  | `digdigdoc-db-superuser`       | kubernetes.io/basic-auth    | CNPG (superuserSecret)                |
| `digdigdoc-db-appuser`    | `digdigdoc-db-appuser`         | kubernetes.io/basic-auth    | CNPG (initdb.secret)                  |
| `digdigdoc-db-infos`      | `digdigdoc-db-appuser`         | Opaque (transformé)         | backend, job de migration             |
| `digdigdoc-db-backups`    | `digdigdoc-db-backups`         | Opaque                      | CNPG (barmanObjectStore)              |
| `registry-pull-secret`    | — (manuel ou ArgoCD)           | kubernetes.io/dockerconfigjson | Tous les pods (imagePullSecrets)    |

---

## 1. `digdigdoc-s3` — Stockage objet S3

Variables attendues dans Vault :

| Variable          | Description                                      | Exemple                          |
| ----------------- | ------------------------------------------------ | -------------------------------- |
| `S3_ACCESS_KEY`   | Clé d'accès S3 (access key ID)                    | `AKIA...`                        |
| `S3_SECRET_KEY`   | Clé secrète S3 (secret access key)               | `xxxxxxxxxxxx`                   |
| `S3_BUCKET`       | Nom du bucket S3                                 | `digdigdoc-prod`                 |
| `S3_REGION`       | Région S3                                        | `fr-par`                         |
| `S3_ENDPOINT_URL` | Endpoint S3 (sans scheme si via `AWS_ENDPOINT_URL`) | `s3.fr-par.scw.cloud`         |

> **Note** : `AWS_ENDPOINT_URL` est défini en clair dans `common-values.yaml` (`https://s3.fr-par.scw.cloud`).
> Seules les credentials (`S3_ACCESS_KEY`, `S3_SECRET_KEY`) et le bucket/région viennent du secret.

**Consommateurs** : backend (`StorageSettings`), worker_document (`WorkerSettings`),
worker_agent (`WorkerSettings`).

---

## 2. `digdigdoc-keycloak` — Authentification Keycloak

Variables attendues dans Vault :

| Variable                  | Description                                              | Exemple                              |
| ------------------------- | -------------------------------------------------------- | ------------------------------------ |
| `KEYCLOAK_URL`            | URL interne Keycloak (backend → Keycloak, Docker service) | `http://keycloak:8080`             |
| `KEYCLOAK_PUBLIC_URL`     | URL publique Keycloak (navigateur, si différente)        | `https://sso.example.com`           |
| `KEYCLOAK_CLIENT_SECRET`  | Secret client OAuth2 (confidentiel)                      | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxx`  |
| `BACKEND_PUBLIC_URL`      | URL publique du backend (pour `redirect_uri`)            | `https://api.example.com`           |
| `FRONTEND_URL`            | URL publique du frontend (redirect post-login/logout)    | `https://app.example.com`           |
| `SHARE_SECRET_KEY`        | Clé HMAC pour les liens de partage d'analyse (magic link) | (aléatoire, 32+ caractères)        |
| `INTERNAL_WORKER_TOKEN`   | Token partagé pour l'authentification des workers sur `/api/internal/*` | (aléatoire, 32+ caractères) |

> **Variables en clair** (dans `common-values.yaml`, pas dans le secret) :
> `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `SESSION_COOKIE_SECURE`.

**Consommateurs** : backend (`KeycloakSettings`, `SharingSettings`).

---

## 3. `digdigdoc-openai` — Hub LLM (compatible API OpenAI)

Variables attendues dans Vault :

| Variable              | Description                                          | Exemple                              |
| --------------------- | ---------------------------------------------------- | ------------------------------------ |
| `OPENAI_API_KEY`      | Clé API pour le hub LLM                              | `sk-xxxxxxxx`                        |
| `OPENAI_API_BASE_URL` | URL de base du hub LLM (compatible OpenAI)          | `https://llm-hub.example.com/v1`    |

> **Note** : `OPENAI_API_BASE_URL` est aussi défini en clair dans `common-values.yaml`
> (commenté). Si la valeur est publique, elle peut rester en clair ; sinon la mettre dans le secret.

**Consommateurs** : backend (`LlmSettings`).

---

## 4. `digdigdoc-worker` — Configuration partagée des workers

Variables attendues dans Vault :

| Variable                | Description                                                        | Exemple                              |
| ----------------------- | ------------------------------------------------------------------ | ------------------------------------ |
| `INTERNAL_WORKER_TOKEN` | Token pour l'authentification des workers sur `/api/internal/*`     | (identique à `digdigdoc-keycloak`)   |
| `OPENAI_API_KEY`        | Clé API pour le hub LLM (VLM + LLM classification/extraction)     | `sk-xxxxxxxx`                        |
| `OPENAI_API_BASE_URL`   | URL de base du hub LLM                                             | `https://llm-hub.example.com/v1`    |
| `VLM_MODEL`             | Modèle vision pour la description des pages (worker_agent)         | `pixtral-12b-2409`                   |
| `LLM_MODEL`             | Modèle texte pour classification/extraction (worker_agent)        | `llama-3.3-70b-instruct`             |

> **Important** : `INTERNAL_WORKER_TOKEN` doit être **identique** à celui du secret
> `digdigdoc-keycloak` (le backend le vérifie, les workers l'envoient).

**Consommateurs** : worker_document, worker_agent.

---

## 5. `digdigdoc-redis` — Redis (broker Celery + checkpointer LangGraph)

Variables attendues dans Vault :

| Variable          | Description                                                        | Exemple                              |
| ----------------- | ------------------------------------------------------------------ | ------------------------------------ |
| `REDIS_PASSWORD`  | Mot de passe Redis                                                 | (aléatoire, 24+ caractères)          |

> **Transformation VSO** : le secret K8s généré contient en plus une variable `REDIS_URL`
> calculée automatiquement :
> ```
> redis://:<REDIS_PASSWORD>@digdigdoc-redis:6379/0
> ```

**Consommateurs** :
- backend (`RedisSettings` → `REDIS_URL`)
- worker_document, worker_agent (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`)
- redis sub-chart (`auth.existingSecret`)
- KEDA `TriggerAuthentication` (pour le scaling sur la longueur de queue)

---

## 6. `digdigdoc-meilisearch` — Meilisearch (recherche)

Variables attendues dans Vault :

| Variable              | Description                          | Exemple                              |
| --------------------- | ------------------------------------ | ------------------------------------ |
| `MEILISEARCH_URL`     | URL du service Meilisearch           | `http://digdigdoc-meilisearch:7700`  |
| `MEILISEARCH_API_KEY` | Clé API Meilisearch                  | (aléatoire, 32+ caractères)          |

> **Note** : ce secret est référencé dans le `envFrom` du backend mais n'est pas encore
> consommé par le code applicatif (`backend/app/config/` n'a pas de `MeilisearchSettings`).
> Il est probablement réservé pour une fonctionnalité future.

**Consommateurs** : backend (envFrom).

---

## 7. `digdigdoc-db-superuser` — Superuser PostgreSQL (CNPG)

Type : `kubernetes.io/basic-auth` (CNPG l'exige, pas Opaque).

Variables attendues dans Vault :

| Variable   | Description                          | Exemple              |
| ---------- | ------------------------------------ | -------------------- |
| `username` | Nom du superuser PostgreSQL          | `postgres`           |
| `password` | Mot de passe du superuser            | (aléatoire, 24+ car.) |

> **Type** : `kubernetes.io/basic-auth` — obligatoire pour CNPG `superuserSecret`.

**Consommateurs** : CNPG (`cluster.superuserSecret`).

---

## 8. `digdigdoc-db-appuser` — Utilisateur applicatif PostgreSQL (CNPG)

Type : `kubernetes.io/basic-auth` (CNPG l'exige, pas Opaque).

Variables attendues dans Vault :

| Variable   | Description                          | Exemple              |
| ---------- | ------------------------------------ | -------------------- |
| `username` | Nom de l'utilisateur applicatif      | `digdigdoc`          |
| `password` | Mot de passe de l'utilisateur app.   | (aléatoire, 24+ car.) |

> **Transformation VSO** : le secret `digdigdoc-db-infos` (ci-dessous) est généré à partir
> de ce même chemin Vault, avec une transformation qui crée `DATABASE_URL`.

**Consommateurs** : CNPG (`cluster.initdb.secret`).

---

## 9. `digdigdoc-db-infos` — URL de connexion base de données (calculée)

Ce secret est **généré par transformation VSO** à partir du chemin Vault `digdigdoc-db-appuser`.

Variables dans le secret K8s généré :

| Variable       | Description                                                        | Source                              |
| -------------- | ------------------------------------------------------------------ | ----------------------------------- |
| `DATABASE_URL` | URL de connexion SQLAlchemy (asyncpg)                              | Calculée : `postgresql+asyncpg://<username>:<password>@digdigdoc-pg-cluster-rw:5432/digdigdoc` |

> **Transformation** : VSO lit `username` et `password` depuis le chemin Vault
> `digdigdoc-db-appuser` et construit la `DATABASE_URL` complète.
> Le `excludes: [".*"]` masque `username`/`password` dans le secret final (seul `DATABASE_URL` est exposé).

**Consommateurs** : backend (`DatabaseSettings`), job de migration Alembic.

---

## 10. `digdigdoc-db-backups` — Credentials S3 pour les backups CNPG

Variables attendues dans Vault :

| Variable              | Description                                          | Exemple                          |
| --------------------- | ---------------------------------------------------- | -------------------------------- |
| `AWS_ACCESS_KEY_ID`   | Clé d'accès S3 pour les backups                      | `AKIA...`                        |
| `AWS_SECRET_ACCESS_KEY` | Clé secrète S3 pour les backups                    | `xxxxxxxxxxxx`                   |
| `AWS_REGION`          | Région du bucket de backup                           | `fr-par`                         |

> **Note** : le bucket et l'endpoint sont définis en clair dans `common-values.yaml`
> (`endpointURL: https://s3.fr-par.scw.cloud`). Seules les credentials viennent du secret.

**Consommateurs** : CNPG (`backups.secret`, `recovery.secret`, `replica.origin.objectStore.secret`).

---

## 11. `registry-pull-secret` — Pull secret du registry Harbor

Type : `kubernetes.io/dockerconfigjson`.

Ce secret n'est **pas** géré par Vault/VSO. Il doit être créé manuellement (ou via ArgoCD) :

```bash
kubectl create secret docker-registry registry-pull-secret \
  --docker-server=harbor.sdid.cpin.numerique-interieur.com \
  --docker-username=<username> \
  --docker-password=<password> \
  --docker-email=<email> \
  -n <namespace>
```

**Consommateurs** : tous les pods (via `global.imagePullSecrets`).

---

## Commandes Vault de référence

### Lister les chemins Vault existants

```bash
vault kv list mirai/
```

### Lire un secret Vault

```bash
vault kv get mirai/digdigdoc-s3
```

### Créer / mettre à jour un secret Vault

```bash
# Exemple : digdigdoc-s3
vault kv put mirai/digdigdoc-s3 \
  S3_ACCESS_KEY="AKIA..." \
  S3_SECRET_KEY="xxxxxxxxxxxx" \
  S3_BUCKET="digdigdoc-prod" \
  S3_REGION="fr-par" \
  S3_ENDPOINT_URL="s3.fr-par.scw.cloud"

# Exemple : digdigdoc-keycloak
vault kv put mirai/digdigdoc-keycloak \
  KEYCLOAK_URL="http://keycloak:8080" \
  KEYCLOAK_PUBLIC_URL="https://sso.example.com" \
  KEYCLOAK_CLIENT_SECRET="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxx" \
  BACKEND_PUBLIC_URL="https://api.example.com" \
  FRONTEND_URL="https://app.example.com" \
  SHARE_SECRET_KEY="$(openssl rand -hex 32)" \
  INTERNAL_WORKER_TOKEN="$(openssl rand -hex 32)"

# Exemple : digdigdoc-openai
vault kv put mirai/digdigdoc-openai \
  OPENAI_API_KEY="sk-xxxxxxxx" \
  OPENAI_API_BASE_URL="https://llm-hub.example.com/v1"

# Exemple : digdigdoc-worker
vault kv put mirai/digdigdoc-worker \
  INTERNAL_WORKER_TOKEN="<identique à digdigdoc-keycloak>" \
  OPENAI_API_KEY="sk-xxxxxxxx" \
  OPENAI_API_BASE_URL="https://llm-hub.example.com/v1" \
  VLM_MODEL="pixtral-12b-2409" \
  LLM_MODEL="llama-3.3-70b-instruct"

# Exemple : digdigdoc-redis
vault kv put mirai/digdigdoc-redis \
  REDIS_PASSWORD="$(openssl rand -base64 24)"

# Exemple : digdigdoc-meilisearch
vault kv put mirai/digdigdoc-meilisearch \
  MEILISEARCH_URL="http://digdigdoc-meilisearch:7700" \
  MEILISEARCH_API_KEY="$(openssl rand -hex 32)"

# Exemple : digdigdoc-db-superuser (type: kubernetes.io/basic-auth)
vault kv put mirai/digdigdoc-db-superuser \
  username="postgres" \
  password="$(openssl rand -base64 24)"

# Exemple : digdigdoc-db-appuser (type: kubernetes.io/basic-auth)
vault kv put mirai/digdigdoc-db-appuser \
  username="digdigdoc" \
  password="$(openssl rand -base64 24)"

# Exemple : digdigdoc-db-backups
vault kv put mirai/digdigdoc-db-backups \
  AWS_ACCESS_KEY_ID="AKIA..." \
  AWS_SECRET_ACCESS_KEY="xxxxxxxxxxxx" \
  AWS_REGION="fr-par"
```

---

## Vérification post-déploiement

```bash
# Lister les secrets K8s générés par VSO
kubectl get secrets -n <namespace> | grep digdigdoc

# Vérifier le contenu d'un secret
kubectl get secret digdigdoc-s3 -n <namespace> -o jsonpath='{.data}' | jq 'to_entries[] | "\(.key): \(.value | @base64d)\n"'

# Vérifier que les VaultStaticSecrets sont synchronisés
kubectl get vaultstaticsecret -n <namespace>
```

---

## Notes importantes

1. **`INTERNAL_WORKER_TOKEN`** doit être **identique** entre `digdigdoc-keycloak` et
   `digdigdoc-worker` — le backend le vérifie côté `/api/internal/*`, les workers l'envoient
   en header `Authorization`.

2. **`digdigdoc-db-infos`** n'a pas de chemin Vault propre — il est généré par transformation
   VSO à partir de `digdigdoc-db-appuser` (même chemin Vault, `DATABASE_URL` calculée).

3. **`digdigdoc-db-superuser` et `digdigdoc-db-appuser`** doivent être de type
   `kubernetes.io/basic-auth` (pas Opaque) — CNPG l'exige pour `superuserSecret` et
   `initdb.secret`.

4. **`BACKEND_API_URL` vs `BACKEND_INTERNAL_URL`** : le chart définit `BACKEND_API_URL`
   en clair dans `common-values.yaml`, mais le code des workers attend `BACKEND_INTERNAL_URL`.
   Vérifier que la variable correcte est utilisée (potentiellement à corriger dans le chart).

5. **`REDIS_URL`** est calculée par transformation VSO à partir de `REDIS_PASSWORD` —
   ne pas la stocker manuellement dans Vault.
