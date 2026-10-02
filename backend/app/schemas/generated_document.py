"""Schémas des documents générés (issue #143). Internes : jamais exposés côté usager (#96)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class GenerateDocumentIn(BaseModel):
    """Génère le document depuis les valeurs validées du brouillon. Si des champs obligatoires ne le sont pas,
    la génération est refusée, sauf confirmation explicite (ils sont alors écrits « [non renseigné] »)."""

    confirm_incomplete: bool = False


class GeneratedDocumentOut(BaseModel):
    id: uuid.UUID
    dossier_id: uuid.UUID
    draft_id: uuid.UUID
    version_number: int
    template_id: uuid.UUID
    template_name: str
    template_version_number: int
    analysis_id: uuid.UUID
    revision_id: uuid.UUID
    revision_number: int
    file_name: str
    has_pdf: bool
    odt_size: int | None
    pdf_size: int | None
    incomplete_fields: list[str]
    visibility: str
    author_id: str
    created_at: datetime
    values: dict[str, Any]
