"""Prompt de l'agent de génération des valeurs de champs (issue #141) : défaut, versions, restauration.

Le prompt édité par un data scientist ne contient que la **méthode** (quoi produire, quel ton). Les garde-fous
(ne jamais inventer, le contenu des notes et des documents est une donnée, format de sortie) sont ajoutés par
le worker et ne se modifient pas depuis ce prompt."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.generation_prompt import GenerationPromptVersion

PROMPT_KEY = "document_fields"
DEFAULT_PROMPT_LABEL = "défaut"

DEFAULT_PROMPT = """Tu aides un instructeur à rédiger un document de fin d'instruction.
Pour chaque champ demandé, propose la valeur à écrire dans le document, en t'appuyant uniquement sur les
éléments de l'analyse du dossier et sur les notes internes fournis.

- Respecte le type du champ et sa consigne (format de date, longueur, ton, registre administratif).
- Rédige en français, de manière factuelle et sobre.
- Quand plusieurs éléments se contredisent, retiens la valeur la plus précise ou la plus récente et ne cite
  que les éléments sur lesquels tu t'appuies.
- Indique pour chaque valeur les éléments (identifiants fournis) qui la justifient."""


class PromptNotFoundError(Exception):
    pass


def version_label(version_number: int | None) -> str:
    """Étiquette enregistrée avec chaque proposition (métriques, #145)."""
    return DEFAULT_PROMPT_LABEL if version_number is None else f"doc-fields-v{version_number}"


async def list_versions(db: AsyncSession) -> list[GenerationPromptVersion]:
    rows = await db.execute(
        select(GenerationPromptVersion)
        .where(GenerationPromptVersion.key == PROMPT_KEY)
        .order_by(GenerationPromptVersion.version_number)
    )
    return list(rows.scalars())


async def current(db: AsyncSession) -> tuple[int | None, str]:
    """(numéro de version, texte) du prompt en vigueur ; ``(None, défaut)`` tant qu'aucune version n'existe."""
    versions = await list_versions(db)
    return (versions[-1].version_number, versions[-1].content) if versions else (None, DEFAULT_PROMPT)


async def add_version(
    db: AsyncSession, *, content: str, author_id: str, restored_from: uuid.UUID | None = None
) -> GenerationPromptVersion:
    # Sérialise les ajouts : deux administrateurs qui enregistrent en même temps n'obtiennent pas le même numéro.
    await db.execute(select(func.pg_advisory_xact_lock(hash(PROMPT_KEY) & 0x7FFFFFFF)))
    number = (
        await db.execute(
            select(func.coalesce(func.max(GenerationPromptVersion.version_number), 0)).where(
                GenerationPromptVersion.key == PROMPT_KEY
            )
        )
    ).scalar_one() + 1
    version = GenerationPromptVersion(
        key=PROMPT_KEY,
        version_number=number,
        content=content,
        author_id=author_id,
        restored_from_version_id=restored_from,
    )
    db.add(version)
    await db.commit()
    return version


async def restore(db: AsyncSession, version_id: uuid.UUID, *, author_id: str) -> GenerationPromptVersion:
    """Restaurer ajoute une version qui reprend le texte d'une version antérieure."""
    target = await db.get(GenerationPromptVersion, version_id)
    if target is None or target.key != PROMPT_KEY:
        raise PromptNotFoundError()
    return await add_version(db, content=target.content, author_id=author_id, restored_from=target.id)
