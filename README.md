# dig-dig-doc

## Configuration

```bash
cp .env.example .env
```

`docker compose up` charge automatiquement ce `.env` à la racine pour
remplir les `${VARIABLE}` de `docker-compose.yaml` (secrets internes, hub
LLM...). `.env.example` est versionné (placeholders, aucun secret réel) ;
`.env` ne l'est jamais (voir `.gitignore`). Détail des variables : voir
[backend/README.md](backend/README.md).
