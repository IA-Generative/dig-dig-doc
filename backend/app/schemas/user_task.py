"""Schémas Pydantic pour les tâches utilisateur (issue #62).

Un ``UserTask`` représente une tâche asynchrone (Celery) lancée par un
utilisateur, persistée pour permettre le suivi de progression côté UI.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.user_task import UserTaskKind, UserTaskStatus


class UserTaskOut(BaseModel):
    """Représentation d'une tâche utilisateur côté API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Identifiant unique de la tâche")
    kind: UserTaskKind = Field(
        description="Type de tâche (text_extraction, classification, …)"
    )
    status: UserTaskStatus = Field(
        description="Statut: pending, running, success ou failure"
    )
    label: str = Field(description="Libellé humain affiché dans l'UI")
    celery_task_id: str | None = Field(
        default=None, description="Identifiant Celery (si applicable)"
    )
    target_id: UUID | None = Field(
        default=None,
        description="ID de l'élément cible (dossier, document, conversation…)",
    )
    target_type: str | None = Field(
        default=None, description="Type de la cible (dossier, document, conversation…)"
    )
    error: str | None = Field(
        default=None, description="Message d'erreur en cas d'échec"
    )
    started_at: datetime | None = Field(default=None, description="Passage en RUNNING")
    ended_at: datetime | None = Field(
        default=None, description="Fin (SUCCESS ou FAILURE)"
    )
    created_at: datetime = Field(description="Création de la ligne (= dispatch)")


class UserTaskUpdateIn(BaseModel):
    """Payload de mise à jour d'une tâche (callback interne worker → backend).

    Seuls les champs mutables sont exposés : ``status``, ``error`` et les
    horodatages. Le worker met à jour la tâche au fil de son exécution.
    """

    status: UserTaskStatus
    error: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
