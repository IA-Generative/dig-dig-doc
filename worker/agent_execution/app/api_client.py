import os

import httpx

BACKEND_INTERNAL_URL = os.environ.get("BACKEND_INTERNAL_URL", "http://localhost:8000")
# Même jeton que côté backend (voir app.core.security.internal.verify_app_token) :
# soit le secret de bootstrap fixe (dev local, docker-compose), soit le
# jeton en clair d'un AppToken créé via POST /api/app-tokens (prod,
# révocable indépendamment) - les deux marchent avec la même variable
# d'environnement, sans changement de code ici.
APP_TOKEN = os.environ.get("INTERNAL_WORKER_TOKEN", "")


def get_client() -> httpx.Client:
    """Client HTTP authentifié vers le BFF, pour tous les appels à
    /api/internal/* (logs d'exécution, réponse de l'agent avec ses
    sources...)."""
    return httpx.Client(base_url=f"{BACKEND_INTERNAL_URL}/api/internal", headers={"X-App-Token": APP_TOKEN})
