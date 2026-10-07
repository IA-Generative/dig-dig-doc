import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.analyse import StatusDefinitionOut
from app.schemas.dossier import DueInfoOut, PersonOut


class TrackingAnalyseOut(BaseModel):
    id: uuid.UUID
    name: str


class TrackingRowOut(BaseModel):
    """Une ligne du tableau de suivi (issue #173) : ce qu'il faut pour piloter, sans le contenu du dossier."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    # Référence lisible (« DOS-2026-0042 »).
    reference: str
    name: str
    analyse: TrackingAnalyseOut
    status: StatusDefinitionOut | None
    assignee: PersonOut | None
    # Qui voit le dossier (#177) : « restricted » (pastille « Restreint ») ou « analyse ».
    visibility: str
    # Échéance et niveau calculé selon les seuils de l'analyse (#172).
    due_at: date | None
    due: DueInfoOut | None
    created_at: datetime
    # Dernière action enregistrée au journal, consultations exclues ; à défaut, la création.
    last_activity_at: datetime
