import uuid
from datetime import date, datetime, timedelta
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.due_date import PARIS

# Un créneau tient dans une journée de travail : la limite évite un créneau « tout le mois ».
MAX_SLOT_DURATION = timedelta(hours=24)
MAX_REMINDERS = 3
# Un rappel se règle jusqu'à 60 jours avant.
MAX_REMINDER_MINUTES = 60 * 24 * 60


class EndNever(BaseModel):
    type: Literal["never"]


class EndUntil(BaseModel):
    """Jusqu'à ce jour inclus."""

    type: Literal["until"]
    date: date


class EndCount(BaseModel):
    type: Literal["count"]
    count: int = Field(ge=1, le=1000)


class RecurrenceIn(BaseModel):
    """Répétition façon calendrier : « tous les ``interval`` jours / semaines / mois / ans »."""

    unit: Literal["day", "week", "month", "year"]
    interval: int = Field(ge=1, le=999)
    # Jours de la semaine concernés (0 = lundi … 6 = dimanche), pour ``unit: week`` ; absent = le jour du créneau.
    weekdays: list[Annotated[int, Field(ge=0, le=6)]] | None = None
    end: Annotated[EndNever | EndUntil | EndCount, Field(discriminator="type")]

    @field_validator("weekdays")
    @classmethod
    def _sorted_unique(cls, weekdays: list[int] | None) -> list[int] | None:
        return sorted(set(weekdays)) if weekdays else None

    @model_validator(mode="after")
    def _weekdays_only_for_weeks(self) -> "RecurrenceIn":
        if self.weekdays and self.unit != "week":
            raise ValueError("Les jours de la semaine ne s'appliquent qu'à une répétition hebdomadaire.")
        return self


class SlotIn(BaseModel):
    start: datetime
    end: datetime
    recurrence: RecurrenceIn | None = None
    # Minutes avant chaque occurrence (0 = à l'heure) ; 3 au plus, sans doublon.
    reminders: list[Annotated[int, Field(ge=0, le=MAX_REMINDER_MINUTES)]] = Field(default_factory=list)

    @field_validator("start", "end")
    @classmethod
    def _timezone_required(cls, value: datetime) -> datetime:
        # Un horaire sans fuseau est ambigu (heure d'été) : le client envoie des instants (ISO avec fuseau).
        if value.tzinfo is None:
            raise ValueError("L'horaire doit préciser son fuseau (ex. 2026-10-08T09:00:00+02:00).")
        return value

    @field_validator("reminders")
    @classmethod
    def _reminders_limits(cls, reminders: list[int]) -> list[int]:
        if len(reminders) > MAX_REMINDERS:
            raise ValueError(f"Un créneau a {MAX_REMINDERS} rappels au plus.")
        return sorted(set(reminders))

    @model_validator(mode="after")
    def _coherent(self) -> "SlotIn":
        if self.end <= self.start:
            raise ValueError("La fin du créneau doit être après son début.")
        if self.end - self.start > MAX_SLOT_DURATION:
            raise ValueError("Un créneau dure 24 heures au plus.")
        end = self.recurrence.end if self.recurrence else None
        if isinstance(end, EndUntil) and end.date < self.start.astimezone(PARIS).date():
            raise ValueError("La fin de la répétition ne peut pas précéder le premier créneau.")
        return self


class SlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dossier_id: uuid.UUID
    start: datetime = Field(validation_alias="start_at")
    end: datetime = Field(validation_alias="end_at")
    recurrence: dict | None
    reminders: list[int]
    updated_at: datetime
