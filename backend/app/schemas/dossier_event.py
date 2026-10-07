import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.dossier_event import DossierEventType


class DossierEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    # Texte (et non l'enum) : un type ajouté plus tard ne casse pas la lecture d'anciens clients.
    type: str
    # None : action du système (fin d'analyse par un worker, historique antérieur au journal).
    actor_id: str | None
    actor_name: str | None
    created_at: datetime
    # Valeurs nécessaires à l'affichage (ancien → nouveau statut, identifiants…), jamais de contenu du dossier.
    payload: dict


class DossierEventActorOut(BaseModel):
    """Un auteur d'événements du dossier : identifiant et dernier nom affiché."""

    actor_id: str
    actor_name: str | None


__all__ = ["DossierEventActorOut", "DossierEventOut", "DossierEventType"]
