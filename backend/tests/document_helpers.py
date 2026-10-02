"""Fonctions d'aide communes aux tests des brouillons de document (#140) et de leur génération (#141)."""

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi.testclient import TestClient

from app.db import async_session_factory
from app.models.dossier_analysis import (
    AnalysisElement,
    AnalysisElementKind,
    DossierAnalysis,
    ElementVersionOrigin,
)
from app.repositories.document_template_repository import DocumentTemplateRepository
from app.repositories.dossier_analysis_repository import DossierAnalysisRepository
from app.schemas.document_template import FieldDefinition

RUN = uuid.uuid4().hex[:8]


def run(client: TestClient, work: Callable[[Any], Awaitable[Any]]) -> Any:
    """Exécute du code asynchrone avec une session, dans la boucle d'événements du client de test."""

    async def runner() -> Any:
        async with async_session_factory() as session:
            return await work(session)

    return client.portal.call(runner)


def field(name: str, source: dict[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    return {"name": name, "label": name.capitalize(), "source": source or {"kind": "instruction"}, **extra}


def entity(definition_name: str) -> dict[str, Any]:
    return {"kind": "analysis", "element_kind": "entity", "definition_name": definition_name}


def meta(key: str) -> dict[str, Any]:
    return {"kind": "dossier_metadata", "key": key}


def analyse_of(client: TestClient, dossier_id: str) -> str:
    """Analyse (type d'analyse) d'un dossier : un modèle de document appartient à une analyse."""
    return client.get(f"/api/dossiers/{dossier_id}").json()["analyse_id"]


def make_template(client: TestClient, fields: list[dict[str, Any]], name: str = "Décision", *, dossier_id: str) -> str:
    """Crée un modèle dans l'analyse du dossier donné (il ne sert qu'aux dossiers de cette analyse)."""
    definitions = [FieldDefinition.model_validate(f) for f in fields]
    analyse_id = uuid.UUID(analyse_of(client, dossier_id))

    async def create(session: Any) -> str:
        template = await DocumentTemplateRepository(session).create(
            user_id="admin",
            analyse_id=analyse_id,
            name=f"{name} {uuid.uuid4().hex[:8]}",
            description="",
            generation_instructions="",
            fields=definitions,
            placeholders=[d.name for d in definitions],
            file_key_for=lambda tid: f"document-templates/{tid}/v1.odt",
            file_name="m.odt",
            file_size=1,
        )
        return str(template.id)

    return run(client, create)


def make_dossier(client: TestClient) -> tuple[str, DossierAnalysis]:
    analyse_id = client.post("/api/analyses", json={"name": "Analyse doc", "description": "t"}).json()["id"]
    dossier_id = client.post("/api/dossiers", json={"name": f"Dossier {RUN}", "analyse_id": analyse_id}).json()["id"]
    analysis = run(client, lambda s: DossierAnalysisRepository(s).create_analysis(uuid.UUID(dossier_id)))
    return dossier_id, analysis


def add_element(
    client: TestClient,
    analysis: DossierAnalysis,
    kind: AnalysisElementKind,
    name: str,
    value: dict[str, Any],
    page: int | None = 1,
) -> AnalysisElement:
    return run(
        client,
        lambda s: DossierAnalysisRepository(s).create_element(
            analysis,
            kind=kind,
            value=value,
            definition_name=name,
            first_page_number=page,
            origin=ElementVersionOrigin.MODEL,
        ),
    )


def add_entity(client: TestClient, analysis: DossierAnalysis, name: str, value: str, page: int | None = 1):
    return add_element(client, analysis, AnalysisElementKind.ENTITY, name, {"value": value}, page)


def create_draft(client: TestClient, dossier_id: str, template_id: str, **body: Any) -> dict[str, Any]:
    response = client.post(f"/api/dossiers/{dossier_id}/document-drafts", json={"template_id": template_id, **body})
    assert response.status_code == 201, response.text
    return response.json()


def url(dossier_id: str, draft_id: str, suffix: str = "") -> str:
    return f"/api/dossiers/{dossier_id}/document-drafts/{draft_id}{suffix}"


def by_name(draft: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {f["name"]: f for f in draft["fields"]}
