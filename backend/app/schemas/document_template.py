"""Schémas des modèles de document et de leurs champs (issue #138, parent #107)."""

import re
import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

FieldType = Literal["text", "date", "number", "list", "boolean"]

# Nom d'un champ = nom du placeholder dans le fichier ({{ nom }}) : un identifiant, hors mots réservés
# du moteur de gabarit (« loop » : variable des boucles ; les autres sont des littéraux).
_FIELD_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_RESERVED = {"loop", "true", "false", "none", "True", "False", "None", "self", "caller", "varargs", "kwargs"}

# Métadonnées du dossier ou du contexte de génération utilisables comme source.
METADATA_KEYS = (
    "dossier_name",
    "dossier_id",
    "dossier_created_at",
    "dossier_started_at",
    "dossier_ended_at",
    "instructor_name",
    "instructor_email",
    "generated_at",
    # Numéro de la révision de l'analyse dont viennent les valeurs, et numéro de version du document :
    # permettent d'écrire « analyse version N » dans le document (#143).
    "analysis_revision",
    "document_version",
)
# Posées à l'assemblage du fichier (#143), pas à la création du brouillon.
ASSEMBLY_TIME_KEYS = ("generated_at", "document_version")


class AnalysisSource(BaseModel):
    """La valeur vient d'un élément de l'analyse du dossier."""

    kind: Literal["analysis"]
    element_kind: Literal["classification", "entity", "relation", "synthesis", "field"]
    definition_name: str = Field(min_length=1, max_length=200)
    # Valeur retenue par l'instructeur, sinon la valeur prédite. Une seule règle pour l'instant :
    # d'autres (la plus récente, la plus fréquente) viendront avec la validation métier.
    # Un champ de type « list » reprend toutes les occurrences ; les autres, la première.
    selection: Literal["retained_or_predicted"] = "retained_or_predicted"


class InstructionSource(BaseModel):
    """La valeur est renseignée au fil de l'instruction (décision, motif, commentaire)."""

    kind: Literal["instruction"]


class MetadataSource(BaseModel):
    """La valeur vient d'une métadonnée du dossier ou du contexte de génération."""

    kind: Literal["dossier_metadata"]
    key: Literal[METADATA_KEYS]  # type: ignore[valid-type]


FieldSource = Annotated[AnalysisSource | InstructionSource | MetadataSource, Field(discriminator="kind")]


class FieldDefinition(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=200)
    type: FieldType = "text"
    required: bool = True
    # Consigne propre au champ pour l'agent de génération (format de date, longueur, ton).
    instruction: str = Field(default="", max_length=2000)
    source: FieldSource

    @field_validator("name")
    @classmethod
    def _valid_name(cls, name: str) -> str:
        if not _FIELD_NAME.match(name) or name in _RESERVED:
            raise ValueError(f"« {name} » n'est pas un nom de champ valide (lettres, chiffres et _, sans mot réservé)")
        return name

    @field_validator("label")
    @classmethod
    def _strip_label(cls, label: str) -> str:
        label = label.strip()
        if not label:
            raise ValueError("Le libellé est obligatoire")
        return label


class FieldList(BaseModel):
    """Liste de champs d'un modèle : les noms sont uniques (un nom = un placeholder)."""

    fields: list[FieldDefinition]

    @model_validator(mode="after")
    def _unique_names(self) -> "FieldList":
        seen: set[str] = set()
        for field in self.fields:
            if field.name in seen:
                raise ValueError(f"Le champ « {field.name} » est défini plusieurs fois")
            seen.add(field.name)
        return self


class PlaceholderReport(BaseModel):
    """Écarts entre les placeholders du fichier et les champs définis, dans les deux sens."""

    unknown_placeholders: list[str]
    unused_fields: list[str]

    @property
    def ok(self) -> bool:
        return not self.unknown_placeholders and not self.unused_fields


class ImportWarning(BaseModel):
    """Avertissement du contrôle d'un modèle à l'import (#148) : à lire, jamais bloquant."""

    code: str
    level: str
    message: str


class FontReport(BaseModel):
    name: str
    # installed, compatible (mêmes métriques), substituted (la mise en page change) ou unknown.
    status: str
    replaced_by: str | None = None


class TemplateInspectOut(BaseModel):
    """Résultat de la lecture d'un fichier, avant toute définition de champs."""

    placeholders: list[str]
    file_name: str
    file_size: int
    fonts: list[FontReport] = []
    warnings: list[ImportWarning] = []


class TemplateRestoreIn(BaseModel):
    version_id: uuid.UUID


class TemplateVersionOut(BaseModel):
    id: uuid.UUID
    version_number: int
    name: str
    description: str
    generation_instructions: str
    fields: list[FieldDefinition]
    placeholders: list[str]
    warnings: list[ImportWarning] = []
    file_name: str
    file_size: int
    author_id: str
    restored_from_version_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TemplateOut(BaseModel):
    """Un modèle avec sa version courante."""

    id: uuid.UUID
    analyse_id: uuid.UUID | None
    archived: bool
    created_by: str
    created_at: datetime
    updated_at: datetime
    version_number: int
    name: str
    description: str
    generation_instructions: str
    fields: list[FieldDefinition]
    placeholders: list[str]
    warnings: list[ImportWarning] = []
    file_name: str
    file_size: int
    last_author_id: str
