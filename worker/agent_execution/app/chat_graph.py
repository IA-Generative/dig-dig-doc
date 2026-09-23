"""Graphe LangGraph pour le chat (réponse aux messages utilisateur).

Contrairement à agent_graph.py qui exécute des agents one-shot au lancement
du dossier, ce graphe répond aux messages du chat en gardant l'historique
de la conversation. Il :

1. Charge l'historique des messages (user + assistant) depuis la conversation.
2. Injecte les synthèses existantes (ExecutionStep.output des agents) dans
   le prompt système pour donner le contexte du dossier.
3. Exécute le graphe ReAct (agent → tools → agent → ...) avec streaming :
   à chaque appel d'outil, un événement est émis via le callback pour
   informer le frontend en temps réel.
4. Renvoie la réponse finale + les sources consultées (pages/documents
   lus par les outils pendant l'exécution).

Le streaming se fait via un callback `on_event(kind, data)` qui dépose
des chat_events en base (voir tasks/chat.py).
"""

import json
import logging
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from app.config import settings
from app.llm import _client
from app.tools import AgentTools, ConsultedSource

logger = logging.getLogger(__name__)

# Callback pour streamer les événements au frontend. Le kind est un des
# ChatEventKind (tool_call, tool_result, thinking, done, error), data est
# un dict sérialisable en JSON.
EventCallback = Callable[[str, dict], None]


class ChatState(TypedDict, total=False):
    """État du graphe LangGraph de chat."""

    messages: list[dict[str, Any]]
    system_prompt: str
    model: str | None
    tools: AgentTools
    iteration: int
    final_answer: str
    on_event: EventCallback | None


def _build_system_prompt(
    conversation_history: list[dict],
    syntheses: list[dict],
    analyse_description: str | None = None,
) -> str:
    """Construit le prompt système pour le chat : rôle de l'assistant,
    contexte du dossier (synthèses existantes), et consignes de réponse."""
    parts = [
        "Tu es un assistant d'analyse documentaire. Tu aides l'instructeur "
        "à comprendre et exploiter les documents de son dossier.",
        "",
        "Tu as accès à des outils pour rechercher dans les pages du dossier, "
        "lire le contenu d'une page, consulter les classifications et les "
        "entités extraites. Utilise-les pour fonder tes réponses sur les "
        "documents réels du dossier.",
        "",
        "Quand tu cites une information, indique sa source (page, document). "
        "Sois précis et concis. Si tu ne trouves pas l'information, dis-le "
        "clairement plutôt que d'inventer.",
    ]

    if analyse_description:
        parts.extend(["", "--- Objectif de l'analyse ---", analyse_description])

    if syntheses:
        parts.extend(["", "--- Synthèses existantes ---"])
        for s in syntheses:
            label = s.get("label", "Agent")
            output = s.get("output", "")
            if output:
                parts.append(f"\n[{label}]\n{output}")

    return "\n".join(parts)


def _agent_node(state: ChatState) -> ChatState:
    """Nœud agent : appelle le LLM avec l'historique + les outils."""
    client = _client()
    model = state.get("model") or settings.LLM_MODEL
    tools = state["tools"]

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": state["system_prompt"]}
    ]
    messages.extend(state["messages"])

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools.tool_definitions(),
        tool_choice="auto",
        temperature=0.2,
        max_tokens=2000,
    )

    choice = response.choices[0]
    assistant_msg: dict[str, Any] = {
        "role": "assistant",
        "content": choice.message.content or "",
    }

    if choice.message.tool_calls:
        assistant_msg["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in choice.message.tool_calls
        ]

    state["messages"] = state.get("messages", []) + [assistant_msg]
    state["iteration"] = state.get("iteration", 0) + 1
    return state


def _should_continue(state: ChatState) -> str:
    """Condition : continue vers les outils si le LLM a demandé un appel
    d'outil, sinon termine."""
    last_msg = state["messages"][-1] if state.get("messages") else {}
    if last_msg.get("tool_calls"):
        if state.get("iteration", 0) >= settings.AGENT_MAX_ITERATIONS:
            logger.warning(
                "Chat agent reached max iterations (%d), stopping",
                settings.AGENT_MAX_ITERATIONS,
            )
            return "end"
        return "tools"
    state["final_answer"] = last_msg.get("content", "")
    return "end"


def _tools_node(state: ChatState) -> ChatState:
    """Nœud outils : exécute les tool_calls et émet des événements pour
    le streaming (tool_call avant exécution, tool_result après)."""
    tools = state["tools"]
    on_event = state.get("on_event")
    last_msg = state["messages"][-1]
    new_messages: list[dict[str, Any]] = []

    for tc in last_msg.get("tool_calls", []):
        name = tc["function"]["name"]
        try:
            arguments = json.loads(tc["function"]["arguments"])
        except json.JSONDecodeError:
            arguments = {}

        # Émet l'événement tool_call avant l'exécution (le frontend peut
        # afficher "Recherche en cours..." pendant l'exécution).
        if on_event:
            on_event("tool_call", {"tool_name": name, "arguments": arguments})

        logger.info("Chat tool call: %s(%s)", name, arguments)
        result = tools.dispatch_tool(name, arguments)

        # Émet l'événement tool_result avec un aperçu du résultat (les 200
        # premiers caractères) pour que le frontend affiche un résumé.
        if on_event:
            preview = result[:200] + "..." if len(result) > 200 else result
            on_event("tool_result", {"tool_name": name, "preview": preview})

        new_messages.append(
            {
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            }
        )

    state["messages"] = state.get("messages", []) + new_messages
    return state


def build_chat_graph() -> Any:
    """Construit le graphe LangGraph pour le chat.
    Le graphe : agent → (tools → agent)* → END"""
    graph = StateGraph(ChatState)
    graph.add_node("agent", _agent_node)
    graph.add_node("tools", _tools_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent",
        _should_continue,
        {"tools": "tools", "end": END},
    )
    graph.add_edge("tools", "agent")
    return graph.compile()


def run_chat(
    conversation_history: list[dict[str, Any]],
    tools: AgentTools,
    syntheses: list[dict] | None = None,
    analyse_description: str | None = None,
    model: str | None = None,
    on_event: EventCallback | None = None,
) -> tuple[str, list[ConsultedSource]]:
    """Exécute le graphe de chat avec l'historique de conversation et les
    synthèses existantes. Renvoie (réponse, sources consultées).

    Les événements intermédiaires (tool_call, tool_result) sont émis via
    on_event pour le streaming temps réel vers le frontend.
    """
    system_prompt = _build_system_prompt(
        conversation_history, syntheses or [], analyse_description
    )

    graph = build_chat_graph()
    initial_state: ChatState = {
        "messages": conversation_history,
        "system_prompt": system_prompt,
        "model": model,
        "tools": tools,
        "iteration": 0,
        "on_event": on_event,
    }
    final_state = graph.invoke(initial_state)
    answer = final_state.get("final_answer", "")
    if not answer:
        last_msg = final_state.get("messages", [{}])[-1]
        answer = last_msg.get("content", "Aucune réponse produite.")
    sources = tools.consulted_sources()
    logger.info(
        "Chat completed in %d iterations, answer length: %d, sources: %d",
        final_state.get("iteration", 0),
        len(answer),
        len(sources),
    )
    return answer, sources
