from contextvars import ContextVar

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.security.ephemeral import EphemeralIdentity
from app.db import async_session_factory
from app.repositories.app_token_repository import AppTokenRepository

_current_identity: ContextVar[EphemeralIdentity | None] = ContextVar("mcp_identity", default=None)


def get_current_identity() -> EphemeralIdentity:
    """À appeler depuis un tool MCP (voir server.py) - posée par
    BearerTokenAuthMiddleware pour la durée de la requête HTTP en cours.
    Une requête ASGI tourne dans une seule tâche asyncio du début à la fin,
    donc le contextvar posé par le middleware reste visible dans le tool
    appelé plus loin dans la même chaîne d'await."""
    identity = _current_identity.get()
    if identity is None:
        raise RuntimeError("Aucune identité MCP dans ce contexte - BearerTokenAuthMiddleware n'a pas tourné.")
    return identity


class BearerTokenAuthMiddleware:
    """Auth du serveur MCP (voir mcp/README.md du côté client, et
    docs/ephemeral-api.md côté design) : un jeton API existant
    (POST /api/app-tokens), présenté en `Authorization: Bearer <token>` -
    convention MCP/OAuth standard, plutôt que le header `X-App-Token`
    propre à /api/internal/*.

    Volontairement en dehors du mécanisme OAuth 2.1 complet du SDK MCP
    (`AuthSettings` avec `issuer_url`/`resource_server_url`, métadonnées de
    découverte...) : ce serait disproportionné pour envelopper un jeton
    opaque déjà géré côté plateforme, avec la même table/le même
    repository que le reste de l'API (`AppTokenRepository.verify`)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope["headers"])
        authorization = headers.get(b"authorization", b"").decode()
        token = authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else None

        if not token:
            response = JSONResponse({"error": "Missing Authorization: Bearer <token>"}, status_code=401)
            await response(scope, receive, send)
            return

        async with async_session_factory() as db:
            app_token = await AppTokenRepository(db).verify(token)
        if app_token is None:
            response = JSONResponse({"error": "Invalid or revoked token"}, status_code=401)
            await response(scope, receive, send)
            return

        reset_token = _current_identity.set(EphemeralIdentity(id=str(app_token.id), is_app_token=True))
        try:
            await self.app(scope, receive, send)
        finally:
            _current_identity.reset(reset_token)
