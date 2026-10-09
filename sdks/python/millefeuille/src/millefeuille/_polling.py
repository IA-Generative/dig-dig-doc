"""Boucle d'attente générique utilisée par les `wait()`."""

from __future__ import annotations

import time
from collections.abc import Callable

from millefeuille.exceptions import WaitTimeoutError


def poll_until[T](
    fetch: Callable[[], T],
    is_done: Callable[[T], bool],
    *,
    timeout: float | None,
    poll_interval: float,
    what: str,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> T:
    """Appelle `fetch` jusqu'à ce que `is_done` soit vrai. `timeout=None` : attente indéfinie."""
    deadline = None if timeout is None else clock() + timeout
    while True:
        value = fetch()
        if is_done(value):
            return value
        if deadline is not None and clock() + poll_interval > deadline:
            raise WaitTimeoutError(f"Délai de {timeout}s dépassé en attendant {what}.")
        sleep(poll_interval)
