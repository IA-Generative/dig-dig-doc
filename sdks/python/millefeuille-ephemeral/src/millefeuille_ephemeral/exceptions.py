"""Exceptions du SDK éphémère : celles du SDK standard + `TTLValidationError`."""

from millefeuille.exceptions import (
    AuthenticationError,
    ConflictError,
    ConnectionFailedError,
    MilleFeuilleError,
    NotFoundError,
    ServerError,
    ValidationError,
    WaitTimeoutError,
)


class TTLValidationError(ValidationError, ValueError):
    """`ttl_hours` hors bornes (1 à 17520), détecté côté client ou rejeté par le serveur (400)."""


__all__ = [
    "AuthenticationError",
    "ConflictError",
    "ConnectionFailedError",
    "MilleFeuilleError",
    "NotFoundError",
    "ServerError",
    "TTLValidationError",
    "ValidationError",
    "WaitTimeoutError",
]
