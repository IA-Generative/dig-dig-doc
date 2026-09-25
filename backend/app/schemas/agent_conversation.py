import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.agent_chat_event import AgentChatEventKind
from app.models.agent_conversation import AgentMessageRole


class AgentMessageSourceIn(BaseModel):
    dossier_id: uuid.UUID | None = None
    analyse_id: uuid.UUID | None = None
    excerpt: str | None = None


class AgentMessageSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dossier_id: uuid.UUID | None
    analyse_id: uuid.UUID | None
    excerpt: str | None


class AgentMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: AgentMessageRole
    content: str | None
    tool_name: str | None
    data: dict
    created_at: datetime
    sources: list[AgentMessageSourceOut]


class AgentConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_by: str
    title: str | None
    created_at: datetime
    messages: list[AgentMessageOut]


class AgentConversationSummaryOut(BaseModel):
    """Vue légère pour la liste des conversations dans la mini-sidebar de la
    modal - pas l'historique complet, juste de quoi afficher une entrée et y
    naviguer."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    created_at: datetime
    last_message_preview: str | None

    @classmethod
    def from_conversation(cls, conversation) -> "AgentConversationSummaryOut":
        preview = conversation.messages[-1].content if conversation.messages else None
        return cls(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            last_message_preview=preview,
        )


class AgentMessageIn(BaseModel):
    """Message envoyé par l'utilisateur depuis la modal produit."""

    content: str
    # Modèle LLM optionnel pour cette exécution (défaut: settings.LLM_MODEL
    # côté worker). Permet à l'utilisateur de choisir le modèle depuis la
    # modal de l'agent helper.
    model: str | None = None


class AgentChatEventOut(BaseModel):
    """Événement d'exécution du graphe de l'agent helper (streaming),
    consommé par le frontend via SSE - pendant à ChatEventOut."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_conversation_id: uuid.UUID
    kind: AgentChatEventKind
    data: dict


class AgentChatEventIn(BaseModel):
    """Payload pour déposer un événement de chat (worker -> backend)."""

    kind: AgentChatEventKind
    data: dict = {}


# --- Schémas internes (worker agent_execution) ---


class InternalAgentMessageOut(BaseModel):
    """Message de conversation pour le worker (graphe interne). Inclut le
    rôle et le contenu ; les tool_call/tool_result déjà journalisés ne sont
    pas renvoyés ici - le worker reconstruit son propre raisonnement, il n'a
    besoin que des tours user/assistant pour l'historique du dialogue."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: AgentMessageRole
    content: str | None


class InternalAgentConversationOut(BaseModel):
    """Conversation complète pour le worker : historique user/assistant.
    Le worker en a besoin pour construire le contexte du graphe LangGraph
    de l'agent helper."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_by: str
    messages: list[InternalAgentMessageOut]


class InternalAgentMessageIn(BaseModel):
    """Dépôt du message assistant final (worker -> backend), avec sources."""

    content: str
    sources: list[AgentMessageSourceIn] = []
