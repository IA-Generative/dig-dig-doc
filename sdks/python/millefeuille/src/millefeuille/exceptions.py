"""Exceptions typées levées par le SDK."""

from __future__ import annotations

import httpx


class MilleFeuilleError(Exception):
    """Racine de toutes les erreurs du SDK."""

    def __init__(self, message: str, *, status_code: int | None = None, response: httpx.Response | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response


class AuthenticationError(MilleFeuilleError):
    """401 (jeton/session invalide ou absent) ou 403 (droits insuffisants)."""


class NotFoundError(MilleFeuilleError):
    """404 : ressource inexistante, ou hors du périmètre de l'appelant."""


class ConflictError(MilleFeuilleError):
    """409 : opération incompatible avec l'état courant (ex. analyse encore référencée par des runs)."""


class ValidationError(MilleFeuilleError):
    """400/422 : requête rejetée par le serveur."""


class ServerError(MilleFeuilleError):
    """5xx : erreur côté serveur (après épuisement des retries)."""


class ConnectionFailedError(MilleFeuilleError):
    """Erreur réseau ou timeout de requête (après épuisement des retries)."""


class WaitTimeoutError(MilleFeuilleError, TimeoutError):
    """`wait()` a dépassé son `timeout` avant d'atteindre un statut terminal."""
