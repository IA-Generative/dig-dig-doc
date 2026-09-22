import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security.share_token import generate_token, hash_token
from app.models.analyse import (
    Agent,
    AgentTool,
    Analyse,
    EntityDefinition,
    FieldVersion,
    LabelDefinition,
    VersionedField,
)
from app.models.analyse_share import AnalyseShare, AnalyseShareKind

if TYPE_CHECKING:
    from app.schemas.analyse import AgentOut, AnalyseOut


class AnalyseRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _base_query(self):
        return select(Analyse).options(
            selectinload(Analyse.labels),
            selectinload(Analyse.entities),
            selectinload(Analyse.agents),
            selectinload(Analyse.field_versions),
            selectinload(Analyse.shares),
        )

    async def list_all(self) -> Sequence[Analyse]:
        result = await self.db.execute(self._base_query().order_by(Analyse.created_at.desc()))
        return result.scalars().all()

    async def get(self, analyse_id: uuid.UUID) -> Analyse | None:
        result = await self.db.execute(self._base_query().where(Analyse.id == analyse_id))
        return result.scalar_one_or_none()

    async def create(self, *, name: str, description: str) -> Analyse:
        analyse = Analyse(name=name, description=description)
        self.db.add(analyse)
        await self.db.commit()
        await self.db.refresh(analyse)
        return analyse

    # --- Versioning: a single mechanism reused for every editable field ---

    def _record_version(self, analyse: Analyse, field: VersionedField, content, agent: Agent | None = None) -> None:
        self.db.add(
            FieldVersion(analyse_id=analyse.id, agent_id=agent.id if agent else None, field=field, content=content)
        )

    def field_versions(self, analyse: Analyse, field: VersionedField, agent_id: uuid.UUID | None = None):
        return [
            version for version in analyse.field_versions if version.field == field and version.agent_id == agent_id
        ]

    async def restore_field_version(
        self, analyse: Analyse, field: VersionedField, version_id: uuid.UUID, agent: Agent | None = None
    ) -> None:
        agent_id = agent.id if agent else None
        version = next(
            (v for v in analyse.field_versions if v.id == version_id and v.field == field and v.agent_id == agent_id),
            None,
        )
        if version is None:
            return
        await self._apply_field(analyse, field, version.content, agent)

    async def _apply_field(self, analyse: Analyse, field: VersionedField, content, agent: Agent | None) -> None:
        if field == VersionedField.CLASSIFICATION_PROMPT:
            await self.update_classification_prompt(analyse, content)
        elif field == VersionedField.CLASSIFICATION_LABELS:
            await self.update_classification_labels(analyse, [LabelDefinition(**item) for item in content])
        elif field == VersionedField.EXTRACTION_PROMPT:
            await self.update_extraction_prompt(analyse, content)
        elif field == VersionedField.EXTRACTION_ENTITIES:
            await self.update_extraction_entities(analyse, [EntityDefinition(**item) for item in content])
        elif field == VersionedField.AGENT_PROMPT and agent:
            await self.update_agent_prompt(analyse, agent, content)
        elif field == VersionedField.AGENT_TOOLS and agent:
            await self.update_agent_tools(analyse, agent, [AgentTool(t) for t in content])
        elif field == VersionedField.AGENT_OUTPUT and agent:
            await self.update_agent_output(analyse, agent, content)

    # --- Classification ---

    async def update_classification_prompt(self, analyse: Analyse, prompt: str) -> None:
        if analyse.classification_prompt == prompt:
            return
        self._record_version(analyse, VersionedField.CLASSIFICATION_PROMPT, analyse.classification_prompt)
        analyse.classification_prompt = prompt
        await self.db.commit()
        await self.db.refresh(analyse)

    async def update_classification_labels(self, analyse: Analyse, labels: list[LabelDefinition]) -> None:
        snapshot = [{"name": label.name, "definition": label.definition} for label in analyse.labels]
        self._record_version(analyse, VersionedField.CLASSIFICATION_LABELS, snapshot)
        for existing in list(analyse.labels):
            await self.db.delete(existing)
        analyse.labels = [
            LabelDefinition(analyse_id=analyse.id, name=lbl.name, definition=lbl.definition) for lbl in labels
        ]
        await self.db.commit()
        await self.db.refresh(analyse)

    # --- Extraction ---

    async def update_extraction_prompt(self, analyse: Analyse, prompt: str) -> None:
        if analyse.extraction_prompt == prompt:
            return
        self._record_version(analyse, VersionedField.EXTRACTION_PROMPT, analyse.extraction_prompt)
        analyse.extraction_prompt = prompt
        await self.db.commit()
        await self.db.refresh(analyse)

    async def update_extraction_entities(self, analyse: Analyse, entities: list[EntityDefinition]) -> None:
        snapshot = [
            {"name": entity.name, "definition": entity.definition, "type": entity.type} for entity in analyse.entities
        ]
        self._record_version(analyse, VersionedField.EXTRACTION_ENTITIES, snapshot)
        for existing in list(analyse.entities):
            await self.db.delete(existing)
        analyse.entities = [
            EntityDefinition(analyse_id=analyse.id, name=ent.name, definition=ent.definition, type=ent.type)
            for ent in entities
        ]
        await self.db.commit()
        await self.db.refresh(analyse)

    # --- Agents ---

    async def add_agent(
        self, analyse: Analyse, *, name: str, prompt: str, tools: list[AgentTool], output: bool
    ) -> Agent:
        agent = Agent(analyse_id=analyse.id, name=name, prompt=prompt, tools=[t.value for t in tools], output=output)
        self.db.add(agent)
        await self.db.commit()
        await self.db.refresh(analyse)
        return agent

    def get_agent(self, analyse: Analyse, agent_id: uuid.UUID) -> Agent | None:
        return next((a for a in analyse.agents if a.id == agent_id), None)

    async def update_agent_prompt(self, analyse: Analyse, agent: Agent, prompt: str) -> None:
        if agent.prompt == prompt:
            return
        self._record_version(analyse, VersionedField.AGENT_PROMPT, agent.prompt, agent)
        agent.prompt = prompt
        await self.db.commit()
        await self.db.refresh(analyse)

    async def update_agent_tools(self, analyse: Analyse, agent: Agent, tools: list[AgentTool]) -> None:
        new_values = [t.value for t in tools]
        if sorted(agent.tools) == sorted(new_values):
            return
        self._record_version(analyse, VersionedField.AGENT_TOOLS, agent.tools, agent)
        agent.tools = new_values
        await self.db.commit()
        await self.db.refresh(analyse)

    async def update_agent_output(self, analyse: Analyse, agent: Agent, output: bool) -> None:
        if agent.output == output:
            return
        self._record_version(analyse, VersionedField.AGENT_OUTPUT, agent.output, agent)
        agent.output = output
        await self.db.commit()
        await self.db.refresh(analyse)

    # --- Version-derived analyse version label ---

    def get_version_label(self, analyse: Analyse) -> str:
        """v1 at the start, +1 per saved change - every FieldVersion row,
        prompt/labels/entities/agents alike, counts once."""
        return f"v{len(analyse.field_versions) + 1}"

    # --- Serialization: the ORM shape (flat field_versions) doesn't match the
    # API's nested shape (promptVersions/labelsVersions per field), so it's
    # built by hand here rather than relying on Pydantic's from_attributes. ---

    def to_agent_schema(self, analyse: Analyse, agent: Agent) -> "AgentOut":
        from app.schemas.analyse import AgentOut, LabelDefinitionOut, Version  # noqa: F401

        return AgentOut(
            id=agent.id,
            name=agent.name,
            prompt=agent.prompt,
            prompt_versions=[
                Version(id=v.id, content=v.content, created_at=v.created_at)
                for v in self.field_versions(analyse, VersionedField.AGENT_PROMPT, agent.id)
            ],
            tools=[AgentTool(t) for t in agent.tools],
            tools_versions=[
                Version(id=v.id, content=[AgentTool(t) for t in v.content], created_at=v.created_at)
                for v in self.field_versions(analyse, VersionedField.AGENT_TOOLS, agent.id)
            ],
            output=agent.output,
            output_versions=[
                Version(id=v.id, content=v.content, created_at=v.created_at)
                for v in self.field_versions(analyse, VersionedField.AGENT_OUTPUT, agent.id)
            ],
        )

    def to_schema(self, analyse: Analyse) -> "AnalyseOut":
        from app.schemas.analyse import (
            AnalyseOut,
            ClassificationOut,
            EntityDefinitionOut,
            ExtractionOut,
            LabelDefinitionOut,
            Version,
        )

        classification = ClassificationOut(
            prompt=analyse.classification_prompt,
            prompt_versions=[
                Version(id=v.id, content=v.content, created_at=v.created_at)
                for v in self.field_versions(analyse, VersionedField.CLASSIFICATION_PROMPT)
            ],
            labels=[LabelDefinitionOut.model_validate(label) for label in analyse.labels],
            labels_versions=[
                Version(
                    id=v.id,
                    content=[LabelDefinitionOut(id=uuid.uuid4(), **item) for item in v.content],
                    created_at=v.created_at,
                )
                for v in self.field_versions(analyse, VersionedField.CLASSIFICATION_LABELS)
            ],
        )
        extraction = ExtractionOut(
            prompt=analyse.extraction_prompt,
            prompt_versions=[
                Version(id=v.id, content=v.content, created_at=v.created_at)
                for v in self.field_versions(analyse, VersionedField.EXTRACTION_PROMPT)
            ],
            entities=[EntityDefinitionOut.model_validate(entity) for entity in analyse.entities],
            entities_versions=[
                Version(
                    id=v.id,
                    content=[EntityDefinitionOut(id=uuid.uuid4(), **item) for item in v.content],
                    created_at=v.created_at,
                )
                for v in self.field_versions(analyse, VersionedField.EXTRACTION_ENTITIES)
            ],
        )
        return AnalyseOut(
            id=analyse.id,
            name=analyse.name,
            description=analyse.description,
            created_at=analyse.created_at,
            classification=classification,
            extraction=extraction,
            agents=[self.to_agent_schema(analyse, agent) for agent in analyse.agents],
        )

    # --- Partage ---

    async def create_email_share(
        self, analyse: Analyse, *, email: str, expires_in_hours: int, created_by: str
    ) -> tuple[AnalyseShare, str]:
        token = generate_token()
        share = AnalyseShare(
            analyse_id=analyse.id,
            kind=AnalyseShareKind.EMAIL,
            email=email,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC) + timedelta(hours=expires_in_hours),
            created_by=created_by,
        )
        self.db.add(share)
        await self.db.commit()
        await self.db.refresh(share)
        return share, token

    async def create_group_share(self, analyse: Analyse, *, keycloak_group: str, created_by: str) -> AnalyseShare:
        share = AnalyseShare(
            analyse_id=analyse.id,
            kind=AnalyseShareKind.KEYCLOAK_GROUP,
            keycloak_group=keycloak_group,
            created_by=created_by,
        )
        self.db.add(share)
        await self.db.commit()
        await self.db.refresh(share)
        return share

    async def revoke_share(self, share: AnalyseShare) -> None:
        await self.db.delete(share)
        await self.db.commit()

    async def get_share_by_id(self, analyse_id: uuid.UUID, share_id: uuid.UUID) -> AnalyseShare | None:
        result = await self.db.execute(
            select(AnalyseShare).where(AnalyseShare.id == share_id, AnalyseShare.analyse_id == analyse_id)
        )
        return result.scalar_one_or_none()

    async def get_by_share_token(self, token: str) -> Analyse | None:
        result = await self.db.execute(select(AnalyseShare).where(AnalyseShare.token_hash == hash_token(token)))
        share = result.scalar_one_or_none()
        if share is None or (share.expires_at and share.expires_at < datetime.now(UTC)):
            return None
        return await self.get(share.analyse_id)
