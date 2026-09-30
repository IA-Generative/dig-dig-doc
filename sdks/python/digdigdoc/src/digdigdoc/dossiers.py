from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import TYPE_CHECKING

from digdigdoc._files import FileInput, prepare_files
from digdigdoc._polling import poll_until
from digdigdoc.models import Dossier, Page

if TYPE_CHECKING:
    from digdigdoc._http import HTTPClient


class DossiersResource:
    """Ressource `/api/dossiers` (dossiers persistants)."""

    def __init__(self, http: HTTPClient) -> None:
        self._http = http

    def list(self, page: int = 1, page_size: int = 20) -> Page[Dossier]:
        data = self._http.get_json("/dossiers", params={"page": page, "page_size": page_size})
        return Page[Dossier].model_validate(data)

    def create(self, name: str, analyse_id: uuid.UUID | str | None = None) -> Dossier:
        """Crée un dossier, lié ou non à une analyse."""
        body = {"name": name, "analyse_id": str(analyse_id) if analyse_id else None}
        return Dossier.model_validate(self._http.request("POST", "/dossiers", json=body).json())

    def get(self, dossier_id: uuid.UUID | str) -> Dossier:
        """Détail complet : documents, statut, étapes d'exécution, résultats."""
        return Dossier.model_validate(self._http.get_json(f"/dossiers/{dossier_id}"))

    def add_files(self, dossier_id: uuid.UUID | str, files: Iterable[FileInput]) -> Dossier:
        """Upload multipart. Accepte chemins, bytes, objets fichier ou tuples `(nom, contenu[, mimetype])`."""
        response = self._http.request("POST", f"/dossiers/{dossier_id}/documents", files=prepare_files(files))
        return Dossier.model_validate(response.json())

    def launch(self, dossier_id: uuid.UUID | str) -> Dossier:
        """Lance le pipeline asynchrone (utiliser `wait()` pour attendre la fin)."""
        return Dossier.model_validate(self._http.request("POST", f"/dossiers/{dossier_id}/launch").json())

    def stop(self, dossier_id: uuid.UUID | str) -> Dossier:
        return Dossier.model_validate(self._http.request("POST", f"/dossiers/{dossier_id}/stop").json())

    def delete(self, dossier_id: uuid.UUID | str) -> None:
        self._http.request("DELETE", f"/dossiers/{dossier_id}")

    def wait(self, dossier_id: uuid.UUID | str, timeout: float | None = None, poll_interval: float = 2) -> Dossier:
        """Attend un statut terminal (`terminé`, `échec`, `arrêté`).

        Lève `WaitTimeoutError` (sous-classe de `TimeoutError`) si `timeout` est dépassé ; `None` = sans limite.
        """
        return poll_until(
            lambda: self.get(dossier_id),
            lambda dossier: dossier.status.is_terminal,
            timeout=timeout,
            poll_interval=poll_interval,
            what=f"la fin du dossier {dossier_id}",
        )
