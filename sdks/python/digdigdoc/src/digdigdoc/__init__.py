"""SDK Python pour la plateforme dig-dig-doc (API REST persistante)."""

from digdigdoc.client import DigDigDocClient
from digdigdoc.exceptions import (
    AuthenticationError,
    ConflictError,
    ConnectionFailedError,
    DigDigDocError,
    NotFoundError,
    ServerError,
    ValidationError,
    WaitTimeoutError,
)
from digdigdoc.models import Analyse, Dossier, DossierStatus

__version__ = "0.1.0"

__all__ = [
    "Analyse",
    "AuthenticationError",
    "ConflictError",
    "ConnectionFailedError",
    "DigDigDocClient",
    "DigDigDocError",
    "Dossier",
    "DossierStatus",
    "NotFoundError",
    "ServerError",
    "ValidationError",
    "WaitTimeoutError",
]
