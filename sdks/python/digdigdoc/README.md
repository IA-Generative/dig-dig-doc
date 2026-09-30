# digdigdoc

SDK Python pour l'API REST **persistante** de dig-dig-doc (`/api/analyses`, `/api/dossiers`,
`/api/app-tokens`, `/api/models`). Pour les analyses à la volée avec TTL, voir
[`digdigdoc-ephemeral`](../digdigdoc-ephemeral/README.md).

Python 3.12+, client synchrone basé sur `httpx`, entièrement typé (`mypy --strict`).

## Installation

```bash
pip install digdigdoc
```

## Authentification

```python
from digdigdoc import DigDigDocClient

client = DigDigDocClient("https://api.dig-dig-doc.example.fr", bearer_token="<access token Keycloak>")
# ou : session_cookie="<valeur du cookie digdigdoc_session>"
# ou : api_token="ddd_..."  (envoyé dans X-App-Token)
```

> **Limite actuelle du backend** : `X-App-Token` n'est accepté que sur `/api/ephemeral/*` et
> `/api/internal/*`. Les routes de ce SDK exigent un access token Keycloak (`bearer_token`) ou une
> session (`session_cookie`). `client.tokens` (gestion des tokens) est lui aussi réservé à Keycloak.

## Quickstart

```python
analyse = client.analyses.create(name="Vérification CNI", description="Vérifie une CNI")

dossier = client.dossiers.create(name="Dossier #1", analyse_id=analyse.id)
client.dossiers.add_files(dossier.id, ["cni.pdf", "justif_domicile.pdf"])
client.dossiers.launch(dossier.id)

result = client.dossiers.wait(dossier.id, timeout=300)
print(result.status)  # DossierStatus.TERMINE
print(result.execution_steps)  # étapes + sorties des agents
```

Fichiers acceptés : chemins (`str`/`Path`), `bytes`, objets fichier binaires, ou tuples
`(nom, contenu[, mimetype])`.

## API

| Ressource | Méthodes |
|---|---|
| `client.analyses` | `list(page, page_size, q)`, `get`, `create(name, description)`, `delete` |
| `client.dossiers` | `list`, `create(name, analyse_id=None)`, `get`, `add_files`, `launch`, `stop`, `delete`, `wait(timeout, poll_interval)` |
| `client.tokens` | `list`, `create(name)` (jeton en clair renvoyé une seule fois), `revoke` |
| `client.models` | `list()` |

## Typage des entrées et sorties

- **Sorties** : chaque réponse est validée par pydantic (`digdigdoc.models`). Tous les champs du backend
  sont typés, les valeurs fermées sont des enums (`DossierStatus`, `ExecutionStepKind`, `EntityType`,
  `AgentTool`…). Une réponse incomplète ou une valeur d'enum inconnue lève une `ValidationError` pydantic.
- **Entrées** : `AnalyseCreate`, `DossierCreate`, `AppTokenCreate`, `AgentCreate`, `LabelDefinitionIn`,
  `EntityDefinitionIn` reprennent les validations du backend (description/prompt non vides, types d'entité
  et outils valides) et refusent les champs inconnus. Une entrée invalide est rejetée **avant** tout appel réseau.
- **Contrat** : `tests/test_contract.py` compare ces modèles à l'OpenAPI du backend (`sdks/python/openapi.json`)
  et échoue au moindre écart (champ, caractère obligatoire, valeurs d'enum). Après un changement d'API
  côté backend : `sdks/python/scripts/update_openapi.sh`, puis corriger les modèles signalés.

## Erreurs

| HTTP | Exception |
|---|---|
| 401 / 403 | `AuthenticationError` |
| 404 | `NotFoundError` |
| 409 | `ConflictError` |
| 400 / 422 | `ValidationError` |
| 5xx | `ServerError` |
| réseau / timeout | `ConnectionFailedError` |
| `wait()` dépassé | `WaitTimeoutError` (aussi un `TimeoutError`) |

Toutes héritent de `DigDigDocError` (`status_code`, `response`). Les 5xx et erreurs réseau sont
retentés (backoff exponentiel, `max_retries=3`) **uniquement** pour GET/PUT/DELETE : un POST n'est
jamais rejoué, pour ne pas créer de doublon.

## Développement

```bash
uv sync
uv run ruff check . && uv run mypy src && uv run pytest
DIGDIGDOC_BASE_URL=... DIGDIGDOC_BEARER_TOKEN=... uv run pytest -m integration
```
