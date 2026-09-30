"""Exceptions typées levées par le SDK."""

from __future__ import annotations

import httpx


class DigDigDocError(Exception):
    """Racine de toutes les erreurs du SDK."""

    def __init__(self, message: str, *, status_code: int | None = None, response: httpx.Response | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response


class AuthenticationError(DigDigDocError):
    """401 (jeton/session invalide ou absent) ou 403 (droits insuffisants)."""


class NotFoundError(DigDigDocError):
    """404 : ressource inexistante, ou hors du périmètre de l'appelant."""


class ConflictError(DigDigDocError):
    """409 : opération incompatible avec l'état courant (ex. analyse encore référencée par des runs)."""


class ValidationError(DigDigDocError):
    """400/422 : requête rejetée par le serveur."""


class ServerError(DigDigDocError):
    """5xx : erreur côté serveur (après épuisement des retries)."""


class ConnectionFailedError(DigDigDocError):
    """Erreur réseau ou timeout de requête (après épuisement des retries)."""


class WaitTimeoutError(DigDigDocError, TimeoutError):
    """`wait()` a dépassé son `timeout` avant d'atteindre un statut terminal."""
