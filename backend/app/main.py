from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.transport_security import TransportSecuritySettings

from app.config import KeycloakSettings
from app.mcp.auth import BearerTokenAuthMiddleware
from app.mcp.server import mcp_server
from app.routers.admin_reports import router as admin_reports_router
from app.routers.analyses import public_router as analyses_public_router
from app.routers.analyses import router as analyses_router
from app.routers.app_tokens import router as app_tokens_router
from app.routers.assist import router as assist_router
from app.routers.auth import router as auth_router
from app.routers.conversations import router as conversations_router
from app.routers.dossiers import router as dossiers_router
from app.routers.ephemeral import router as ephemeral_router
from app.routers.health import router as health_router
from app.routers.internal import router as internal_router
from app.routers.internal_agent import agent_conversations_router as internal_agent_conversations_router
from app.routers.internal_agent import router as internal_agent_router
from app.routers.models import router as models_router
from app.routers.reports import router as reports_router

_keycloak_settings = KeycloakSettings()

# Streamable HTTP monté sous /mcp (voir mcp/README.md). L'app Starlette
# renvoyée par streamable_http_app() porte son propre lifespan
# (session_manager.run()) : Starlette ne le déclenche jamais tout seul pour
# une sous-app montée via app.mount(), il faut l'entrer explicitement dans
# le lifespan du process qui l'héberge - ici celui du backend.
# streamable_http_path="/" : la route interne est à la racine de cette
# sous-app, montée elle-même sous /mcp juste en dessous - sans ça, l'URL
# finale serait /mcp/mcp (préfixe en double).
#
# transport_security : la protection anti DNS-rebinding du SDK MCP (activée
# par défaut dès que host="127.0.0.1"/"localhost") valide le header Host
# contre une liste fixe - inadaptée ici, ce endpoint est servi derrière le
# même reverse proxy/domaine que le reste de l'API (BACKEND_PUBLIC_URL,
# configurable par déploiement) et protégé par le même Bearer token que
# n'importe quelle route /api/*, pas par du same-origin. Désactivée plutôt
# que maintenue en synchronisation avec BACKEND_PUBLIC_URL.
mcp_app = mcp_server.streamable_http_app(
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp_app.router.lifespan_context(mcp_app):
        yield


app = FastAPI(
    title="dig-dig-doc BFF",
    docs_url="/api/docs",
    redoc_url="/api/redocs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "Auth", "description": "Login/logout via Keycloak, session management."},
        {"name": "Health", "description": "Liveness/readiness of the API and its dependencies."},
        {"name": "Analyses", "description": "Classification, extraction et agents d'une analyse."},
        {"name": "Dossiers", "description": "Dossiers usagers liés à une analyse, et suivi de leur exécution."},
        {"name": "Conversations", "description": "Conversations de l'utilisateur courant, tous dossiers confondus."},
        {"name": "Models", "description": "Modèles LLM disponibles sur le hub configuré, pour peupler un sélecteur."},
        {"name": "Assist", "description": "Chat completion générique utilisée par les boutons d'aide LLM du frontend."},
        {"name": "Internal", "description": "Callbacks des workers Celery (jeton partagé, pas d'auth Keycloak)."},
        {"name": "App tokens", "description": "Jetons permettant à une application externe d'appeler l'API."},
        {"name": "Reports", "description": "Signalements libres (bug/idée/question) envoyés par les utilisateurs."},
        {"name": "Admin", "description": "Vues et actions réservées aux administrateurs."},
        {
            "name": "Ephemeral",
            "description": "Analyses et dossiers à la demande, temporaires par défaut (TTL) - "
            "voir docs/ephemeral-api.md.",
        },
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
app.include_router(models_router, prefix="/api")
app.include_router(assist_router, prefix="/api")
app.include_router(internal_router, prefix="/api")
app.include_router(internal_agent_router, prefix="/api")
app.include_router(internal_agent_conversations_router, prefix="/api")
app.include_router(app_tokens_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(admin_reports_router, prefix="/api")
app.include_router(ephemeral_router, prefix="/api")
app.mount("/mcp", BearerTokenAuthMiddleware(mcp_app))
