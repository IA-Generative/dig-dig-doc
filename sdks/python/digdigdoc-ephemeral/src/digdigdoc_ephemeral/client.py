from __future__ import annotations

import uuid
from collections.abc import Iterable
from types import TracebackType

import httpx
from digdigdoc._files import FileInput
from digdigdoc._http import DEFAULT_TIMEOUT, HTTPClient

from digdigdoc_ephemeral.analyses import EphemeralAnalysesResource
from digdigdoc_ephemeral.models import TTL_DEFAULT_HOURS, EphemeralAnalysisConfig, EphemeralRun
from digdigdoc_ephemeral.runs import EphemeralRunsResource


class EphemeralClient:
    """Client de l'API éphémère : analyses et runs à la volée, avec TTL et purge automatique.

    Authentification (au moins une méthode) : `api_token` (`X-App-Token`, recommandé pour un
    usage programmatique), `bearer_token` (access token Keycloak) ou `session_cookie`.
    """

    def __init__(
        self,
        base_url: str,
        *,
        api_token: str | None = None,
        bearer_token: str | None = None,
        session_cookie: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not (api_token or bearer_token or session_cookie):
            raise ValueError("Fournir api_token, bearer_token ou session_cookie.")
        self._http = HTTPClient(
            base_url=base_url,
            api_token=api_token,
            bearer_token=bearer_token,
            session_cookie=session_cookie,
            timeout=timeout,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            transport=transport,
        )
        self.analyses = EphemeralAnalysesResource(self._http)
        self.runs = EphemeralRunsResource(self._http)

    def analyze(
        self,
        files: Iterable[FileInput],
        analysis_config: EphemeralAnalysisConfig | None = None,
        ttl_hours: int | None = TTL_DEFAULT_HOURS,
        persist: bool = False,
        timeout: float | None = 300,
        *,
        analyse_id: uuid.UUID | str | None = None,
        poll_interval: float = 2,
        cleanup: bool = False,
    ) -> EphemeralRun:
        """One-liner : crée l'analyse éphémère, lance le run, attend le résultat.

        Fournir `analysis_config` (l'analyse est créée) ou `analyse_id` (analyse existante réutilisée).
        `persist` s'applique au run ; l'analyse suit `analysis_config.persist`.
        `cleanup=True` supprime le run (et l'analyse si elle a été créée ici) une fois le résultat
        récupéré : le `EphemeralRun` renvoyé est alors un instantané, plus consultable côté serveur.
        `WaitTimeoutError` est levée si `timeout` est dépassé (le run continue côté serveur).
        """
        if (analysis_config is None) == (analyse_id is None):
            raise ValueError("Fournir exactement un de analysis_config ou analyse_id.")
        created_analyse_id: uuid.UUID | None = None
        if analysis_config is not None:
            created = self.analyses.create_from_config(analysis_config)
            created_analyse_id = created.id
            analyse_id = created.id
        assert analyse_id is not None
        try:
            run = self.runs.create(analyse_id, files, persist=persist, ttl_hours=ttl_hours)
            result = self.runs.wait(run.id, timeout=timeout, poll_interval=poll_interval)
        except BaseException:
            # L'analyse créée ici ne doit pas fuir si le run n'a jamais pu démarrer.
            if created_analyse_id is not None and cleanup:
                self._quiet_delete_analyse(created_analyse_id)
            raise
        if cleanup:
            self.runs.delete(run.id)
            if created_analyse_id is not None:
                self.analyses.delete(created_analyse_id)
        return result

    def _quiet_delete_analyse(self, analyse_id: uuid.UUID) -> None:
        try:
            self.analyses.delete(analyse_id)
        except Exception:  # noqa: BLE001 - nettoyage au mieux, l'erreur d'origine prime
            pass

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> EphemeralClient:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self.close()
