"""SDK Python pour l'API éphémère de dig-dig-doc (analyses et runs à la volée avec TTL)."""

from digdigdoc_ephemeral.client import EphemeralClient
from digdigdoc_ephemeral.exceptions import (
    AuthenticationError,
    ConflictError,
    ConnectionFailedError,
    DigDigDocError,
    NotFoundError,
    ServerError,
    TTLValidationError,
    ValidationError,
    WaitTimeoutError,
)
from digdigdoc_ephemeral.models import (
    AgentDefinition,
    EphemeralAnalyse,
    EphemeralAnalysisConfig,
    EphemeralRun,
)

__version__ = "0.1.0"

__all__ = [
    "AgentDefinition",
    "AuthenticationError",
    "ConflictError",
    "ConnectionFailedError",
    "DigDigDocError",
    "EphemeralAnalysisConfig",
    "EphemeralAnalyse",
    "EphemeralClient",
    "EphemeralRun",
    "NotFoundError",
    "ServerError",
    "TTLValidationError",
    "ValidationError",
    "WaitTimeoutError",
]
