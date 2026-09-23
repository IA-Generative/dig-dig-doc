from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import KeycloakSettings
from app.routers.analyses import public_router as analyses_public_router
from app.routers.analyses import router as analyses_router
from app.routers.app_tokens import router as app_tokens_router
from app.routers.auth import router as auth_router
from app.routers.conversations import router as conversations_router
from app.routers.dossiers import router as dossiers_router
from app.routers.health import router as health_router
from app.routers.internal import router as internal_router

_keycloak_settings = KeycloakSettings()

app = FastAPI(
    title="dig-dig-doc BFF",
    docs_url="/api/docs",
    redoc_url="/api/redocs",
    openapi_url="/api/openapi.json",
    openapi_tags=[
        {"name": "Auth", "description": "Login/logout via Keycloak, session management."},
        {"name": "Health", "description": "Liveness/readiness of the API and its dependencies."},
        {"name": "Analyses", "description": "Classification, extraction et agents d'une analyse."},
        {"name": "Dossiers", "description": "Dossiers usagers liés à une analyse, et suivi de leur exécution."},
        {"name": "Conversations", "description": "Conversations de l'utilisateur courant, tous dossiers confondus."},
        {"name": "Internal", "description": "Callbacks des workers Celery (jeton partagé, pas d'auth Keycloak)."},
        {"name": "App tokens", "description": "Jetons permettant à une application externe d'appeler l'API."},
    ],
)

# Explicit origin (not "*") required: credentialed cookie requests are
# rejected by browsers if allow_origins is a wildcard.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_keycloak_settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth")
app.include_router(health_router, prefix="/api")
app.include_router(analyses_public_router, prefix="/api")
app.include_router(analyses_router, prefix="/api")
app.include_router(dossiers_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")
app.include_router(internal_router, prefix="/api")
app.include_router(app_tokens_router, prefix="/api")
