import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import KeycloakSettings, SharingSettings
from app.core.security.factory import RequestContext, get_current_user
from app.db import get_db
from app.models.analyse import Agent, Analyse, EntityDefinition, LabelDefinition, VersionedField
from app.models.analyse_share import AnalyseShareKind
from app.repositories.analyse_repository import AnalyseRepository
from app.schemas.analyse import (
    AgentCreate,
    AgentOut,
    AnalyseCreate,
    AnalyseListItem,
    AnalyseOut,
    AnalyseShareCreate,
    AnalyseShareOut,
    EntitiesUpdate,
    LabelsUpdate,
    OutputUpdate,
    PromptUpdate,
    ToolsUpdate,
)

router = APIRouter(prefix="/analyses", tags=["Analyses"], dependencies=[Depends(get_current_user)])

# Route de partage publique (lien magique par email) : volontairement sur un
# routeur séparé, sans Depends(get_current_user) - la personne qui ouvre le
# lien n'a pas forcément de compte Keycloak. Monté sous le même préfixe
# /analyses dans main.py ; pas de collision avec GET /analyses/{analyse_id}
# (un seul segment) puisque ce chemin en a deux (shared/{token}).
public_router = APIRouter(prefix="/analyses", tags=["Analyses"])


async def _get_or_404(repository: AnalyseRepository, analyse_id: uuid.UUID) -> Analyse:
    analyse = await repository.get(analyse_id)
    if analyse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyse introuvable")
    return analyse


def _get_agent_or_404(repository: AnalyseRepository, analyse: Analyse, agent_id: uuid.UUID) -> Agent:
    agent = repository.get_agent(analyse, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent introuvable")
    return agent


@router.get("", response_model=list[AnalyseListItem])
async def list_analyses(db: Annotated[AsyncSession, Depends(get_db)]) -> list[AnalyseListItem]:
    repository = AnalyseRepository(db)
    analyses = await repository.list_all()
    return [
        AnalyseListItem(
            id=a.id, name=a.name, description=a.description, created_at=a.created_at, agent_count=len(a.agents)
        )
        for a in analyses
    ]


@router.post("", response_model=AnalyseOut, status_code=status.HTTP_201_CREATED)
async def create_analyse(body: AnalyseCreate, db: Annotated[AsyncSession, Depends(get_db)]) -> AnalyseOut:
    repository = AnalyseRepository(db)
    analyse = await repository.create(name=body.name, description=body.description)
    analyse = await _get_or_404(repository, analyse.id)
    return repository.to_schema(analyse)


@router.get("/{analyse_id}", response_model=AnalyseOut)
async def get_analyse(analyse_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]) -> AnalyseOut:
    repository = AnalyseRepository(db)
    analyse = await _get_or_404(repository, analyse_id)
    return repository.to_schema(analyse)


@router.put("/{analyse_id}/classification/prompt", response_model=AnalyseOut)
async def update_classification_prompt(
    analyse_id: uuid.UUID, body: PromptUpdate, db: Annotated[AsyncSession, Depends(get_db)]
) -> AnalyseOut:
    repository = AnalyseRepository(db)
    analyse = await _get_or_404(repository, analyse_id)
    await repository.update_classification_prompt(analyse, body.prompt)
    return repository.to_schema(analyse)


@router.post("/{analyse_id}/classification/prompt/restore/{version_id}", response_model=AnalyseOut)
async def restore_classification_prompt(
    analyse_id: uuid.UUID, version_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> AnalyseOut:
    repository = AnalyseRepository(db)
    analyse = await _get_or_404(repository, analyse_id)
    await repository.restore_field_version(analyse, VersionedField.CLASSIFICATION_PROMPT, version_id)
    return repository.to_schema(analyse)


@router.put("/{analyse_id}/classification/labels", response_model=AnalyseOut)
async def update_classification_labels(
    analyse_id: uuid.UUID, body: LabelsUpdate, db: Annotated[AsyncSession, Depends(get_db)]
) -> AnalyseOut:
    repository = AnalyseRepository(db)
    analyse = await _get_or_404(repository, analyse_id)
    labels = [LabelDefinition(name=lbl.name, definition=lbl.definition) for lbl in body.labels]
    await repository.update_classification_labels(analyse, labels)
    return repository.to_schema(analyse)


@router.post("/{analyse_id}/classification/labels/restore/{version_id}", response_model=AnalyseOut)
async def restore_classification_labels(
    analyse_id: uuid.UUID, version_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> AnalyseOut:
    repository = AnalyseRepository(db)
    analyse = await _get_or_404(repository, analyse_id)
    await repository.restore_field_version(analyse, VersionedField.CLASSIFICATION_LABELS, version_id)
    return repository.to_schema(analyse)


@router.put("/{analyse_id}/extraction/prompt", response_model=AnalyseOut)
async def update_extraction_prompt(
    analyse_id: uuid.UUID, body: PromptUpdate, db: Annotated[AsyncSession, Depends(get_db)]
) -> AnalyseOut:
    repository = AnalyseRepository(db)
    analyse = await _get_or_404(repository, analyse_id)
    await repository.update_extraction_prompt(analyse, body.prompt)
    return repository.to_schema(analyse)


@router.post("/{analyse_id}/extraction/prompt/restore/{version_id}", response_model=AnalyseOut)
async def restore_extraction_prompt(
    analyse_id: uuid.UUID, version_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> AnalyseOut:
    repository = AnalyseRepository(db)
    analyse = await _get_or_404(repository, analyse_id)
    await repository.restore_field_version(analyse, VersionedField.EXTRACTION_PROMPT, version_id)
    return repository.to_schema(analyse)


@router.put("/{analyse_id}/extraction/entities", response_model=AnalyseOut)
async def update_extraction_entities(
    analyse_id: uuid.UUID, body: EntitiesUpdate, db: Annotated[AsyncSession, Depends(get_db)]
) -> AnalyseOut:
    repository = AnalyseRepository(db)
    analyse = await _get_or_404(repository, analyse_id)
    entities = [EntityDefinition(name=ent.name, definition=ent.definition, type=ent.type) for ent in body.entities]
    await repository.update_extraction_entities(analyse, entities)
    return repository.to_schema(analyse)


@router.post("/{analyse_id}/extraction/entities/restore/{version_id}", response_model=AnalyseOut)
async def restore_extraction_entities(
    analyse_id: uuid.UUID, version_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> AnalyseOut:
    repository = AnalyseRepository(db)
    analyse = await _get_or_404(repository, analyse_id)
    await repository.restore_field_version(analyse, VersionedField.EXTRACTION_ENTITIES, version_id)
    return repository.to_schema(analyse)


@router.post("/{analyse_id}/agents", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
async def add_agent(analyse_id: uuid.UUID, body: AgentCreate, db: Annotated[AsyncSession, Depends(get_db)]) -> AgentOut:
    repository = AnalyseRepository(db)
    analyse = await _get_or_404(repository, analyse_id)
    agent = await repository.add_agent(
        analyse, name=body.name, prompt=body.prompt, tools=body.tools, output=body.output
    )
    analyse = await _get_or_404(repository, analyse_id)
    return repository.to_agent_schema(analyse, repository.get_agent(analyse, agent.id))


@router.put("/{analyse_id}/agents/{agent_id}/prompt", response_model=AgentOut)
async def update_agent_prompt(
    analyse_id: uuid.UUID, agent_id: uuid.UUID, body: PromptUpdate, db: Annotated[AsyncSession, Depends(get_db)]
) -> AgentOut:
    repository = AnalyseRepository(db)
    analyse = await _get_or_404(repository, analyse_id)
    agent = _get_agent_or_404(repository, analyse, agent_id)
    await repository.update_agent_prompt(analyse, agent, body.prompt)
    return repository.to_agent_schema(analyse, agent)


@router.post("/{analyse_id}/agents/{agent_id}/prompt/restore/{version_id}", response_model=AgentOut)
async def restore_agent_prompt(
    analyse_id: uuid.UUID, agent_id: uuid.UUID, version_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> AgentOut:
    repository = AnalyseRepository(db)
    analyse = await _get_or_404(repository, analyse_id)
    agent = _get_agent_or_404(repository, analyse, agent_id)
    await repository.restore_field_version(analyse, VersionedField.AGENT_PROMPT, version_id, agent)
    return repository.to_agent_schema(analyse, agent)


@router.put("/{analyse_id}/agents/{agent_id}/tools", response_model=AgentOut)
async def update_agent_tools(
    analyse_id: uuid.UUID, agent_id: uuid.UUID, body: ToolsUpdate, db: Annotated[AsyncSession, Depends(get_db)]
) -> AgentOut:
    repository = AnalyseRepository(db)
    analyse = await _get_or_404(repository, analyse_id)
    agent = _get_agent_or_404(repository, analyse, agent_id)
    await repository.update_agent_tools(analyse, agent, body.tools)
    return repository.to_agent_schema(analyse, agent)


@router.post("/{analyse_id}/agents/{agent_id}/tools/restore/{version_id}", response_model=AgentOut)
async def restore_agent_tools(
    analyse_id: uuid.UUID, agent_id: uuid.UUID, version_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> AgentOut:
    repository = AnalyseRepository(db)
    analyse = await _get_or_404(repository, analyse_id)
    agent = _get_agent_or_404(repository, analyse, agent_id)
    await repository.restore_field_version(analyse, VersionedField.AGENT_TOOLS, version_id, agent)
    return repository.to_agent_schema(analyse, agent)


@router.put("/{analyse_id}/agents/{agent_id}/output", response_model=AgentOut)
async def update_agent_output(
    analyse_id: uuid.UUID, agent_id: uuid.UUID, body: OutputUpdate, db: Annotated[AsyncSession, Depends(get_db)]
) -> AgentOut:
    repository = AnalyseRepository(db)
    analyse = await _get_or_404(repository, analyse_id)
    agent = _get_agent_or_404(repository, analyse, agent_id)
    await repository.update_agent_output(analyse, agent, body.output)
    return repository.to_agent_schema(analyse, agent)


@router.post("/{analyse_id}/agents/{agent_id}/output/restore/{version_id}", response_model=AgentOut)
async def restore_agent_output(
    analyse_id: uuid.UUID, agent_id: uuid.UUID, version_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> AgentOut:
    repository = AnalyseRepository(db)
    analyse = await _get_or_404(repository, analyse_id)
    agent = _get_agent_or_404(repository, analyse, agent_id)
    await repository.restore_field_version(analyse, VersionedField.AGENT_OUTPUT, version_id, agent)
    return repository.to_agent_schema(analyse, agent)


# --- Partage ---


@router.get("/{analyse_id}/shares", response_model=list[AnalyseShareOut])
async def list_shares(analyse_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    repository = AnalyseRepository(db)
    analyse = await _get_or_404(repository, analyse_id)
    return analyse.shares


@router.post("/{analyse_id}/shares", response_model=AnalyseShareOut, status_code=status.HTTP_201_CREATED)
async def create_share(
    analyse_id: uuid.UUID,
    body: AnalyseShareCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[RequestContext, Depends(get_current_user)],
):
    repository = AnalyseRepository(db)
    analyse = await _get_or_404(repository, analyse_id)

    if body.kind == AnalyseShareKind.EMAIL:
        if not body.email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="email requis")
        ttl = body.expires_in_hours or SharingSettings().SHARE_DEFAULT_TTL_HOURS
        share, token = await repository.create_email_share(
            analyse, email=body.email, expires_in_hours=ttl, created_by=user.user_id
        )
        frontend_url = KeycloakSettings().FRONTEND_URL
        result = AnalyseShareOut.model_validate(share)
        result.share_url = f"{frontend_url}/analyses/shared/{token}"
        return result

    if not body.keycloak_group:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="keycloak_group requis")
    share = await repository.create_group_share(analyse, keycloak_group=body.keycloak_group, created_by=user.user_id)
    return AnalyseShareOut.model_validate(share)


@router.delete("/{analyse_id}/shares/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share(analyse_id: uuid.UUID, share_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    repository = AnalyseRepository(db)
    share = await repository.get_share_by_id(analyse_id, share_id)
    if share is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partage introuvable")
    await repository.revoke_share(share)


@public_router.get("/shared/{token}", response_model=AnalyseOut)
async def get_shared_analyse(token: str, db: Annotated[AsyncSession, Depends(get_db)]):
    repository = AnalyseRepository(db)
    analyse = await repository.get_by_share_token(token)
    if analyse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lien de partage invalide ou expiré")
    return repository.to_schema(analyse)
