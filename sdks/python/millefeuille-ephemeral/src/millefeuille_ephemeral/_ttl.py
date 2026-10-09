from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from millefeuille.exceptions import ValidationError

from millefeuille_ephemeral.exceptions import TTLValidationError
from millefeuille_ephemeral.models import TTL_DEFAULT_HOURS, TTL_MAX_HOURS


def validate_ttl_hours(ttl_hours: int | None) -> int | None:
    """Valide `ttl_hours` côté client ; `None` laisse le serveur appliquer son défaut (24h)."""
    if ttl_hours is not None and not 1 <= ttl_hours <= TTL_MAX_HOURS:
        raise TTLValidationError(
            f"ttl_hours doit être compris entre 1 et {TTL_MAX_HOURS} (défaut {TTL_DEFAULT_HOURS})."
        )
    return ttl_hours


@contextmanager
def translate_ttl_errors() -> Iterator[None]:
    """Un 400 serveur mentionnant `ttl_hours` devient un `TTLValidationError`."""
    try:
        yield
    except ValidationError as error:
        if "ttl_hours" in error.message and not isinstance(error, TTLValidationError):
            raise TTLValidationError(error.message, status_code=error.status_code, response=error.response) from error
        raise
