"""Graphe LangGraph pour l'agent helper (issue #50).

Même structure que chat_graph.py (chat par dossier) : boucle ReAct
agent -> tools -> agent -> ... avec streaming des tool_calls/tool_results
via un callback. Deux différences :

- Pas de dossier chargé en amont ni de synthèses à injecter dans le prompt
  système : l'agent helper part d'une conversation "vide" et découvre/crée
  les dossiers/analyses au fil de l'échange via ses outils (HelperTools).
- Les "sources" de chat_graph.py (pages/documents consultés) deviennent des
  "ressources consultées" (dossiers/analyses touchés), utilisées côté
  frontend pour afficher un lien direct plutôt qu'un extrait de document.
"""

import json
import logging
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from app.config import settings
from app.helper_tools import ConsultedResource, HelperTools
from app.llm import _client

logger = logging.getLogger(__name__)

EventCallback = Callable[[str, dict], None]

_SYSTEM_PROMPT = """Tu es l'agent helper de dig-dig-doc. Tu aides l'utilisateur à retrouver ou \
créer des analyses et des dossiers, à y ajouter des fichiers et à lancer le pipeline \
d'instruction (classification, extraction, agents), en langage naturel.

Outils disponibles : recherche/liste/détail/création d'analyses, recherche/liste/détail/création \
de dossiers, lancement du pipeline sur un dossier, consultation de ses résultats.

Tu ne peux pas ajouter de fichiers toi-même (aucun outil pour ça) : si l'utilisateur veut \
analyser des documents, dis-lui de les déposer via le bouton d'ajout de fichiers de la modal une \
fois le dossier créé, puis de te redemander de lancer le pipeline.

Avant de créer une nouvelle analyse, cherche s'il en existe déjà une pertinente \
(search_analyses) et propose-la plutôt que d'en recréer une similaire. Sois concis. Quand tu \
donnes le résultat d'une action sur un dossier ou une analyse, mentionne son nom pour que \
l'utilisateur puisse le retrouver facilement."""


class HelperState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    tools: HelperTools
    iteration: int
    final_answer: str
    on_event: EventCallback | None
    model: str | None


def _agent_node(state: HelperState) -> HelperState:
    client = _client()
    tools = state["tools"]

    messages: list[dict[str, Any]] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    messages.extend(state["messages"])

    response = client.chat.completions.create(
        model=state.get("model") or settings.LLM_MODEL,
        messages=messages,
        tools=tools.tool_definitions(),
        tool_choice="auto",
        parallel_tool_calls=False,
        temperature=0.2,
        max_tokens=2000,
    )

    choice = response.choices[0]
    assistant_msg: dict[str, Any] = {"role": "assistant", "content": choice.message.content or ""}
    if choice.message.tool_calls:
        assistant_msg["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in choice.message.tool_calls
        ]

    state["messages"] = state.get("messages", []) + [assistant_msg]
    state["iteration"] = state.get("iteration", 0) + 1
    return state


def _should_continue(state: HelperState) -> str:
    last_msg = state["messages"][-1] if state.get("messages") else {}
    if last_msg.get("tool_calls"):
        if state.get("iteration", 0) >= settings.AGENT_MAX_ITERATIONS:
            logger.warning("Helper agent reached max iterations (%d), stopping", settings.AGENT_MAX_ITERATIONS)
            return "end"
        return "tools"
    state["final_answer"] = last_msg.get("content", "")
    return "end"


def _tools_node(state: HelperState) -> HelperState:
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

        if on_event:
            on_event("tool_call", {"tool_name": name, "arguments": arguments})

        logger.info("Helper agent tool call: %s(%s)", name, arguments)
        result = tools.dispatch_tool(name, arguments)

        if on_event:
            preview = result[:200] + "..." if len(result) > 200 else result
            on_event("tool_result", {"tool_name": name, "preview": preview})

        new_messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

    state["messages"] = state.get("messages", []) + new_messages
    return state


def build_helper_graph() -> Any:
    graph = StateGraph(HelperState)
    graph.add_node("agent", _agent_node)
    graph.add_node("tools", _tools_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", _should_continue, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")
    return graph.compile()


def run_helper_chat(
    conversation_history: list[dict[str, Any]],
    tools: HelperTools,
    on_event: EventCallback | None = None,
    model: str | None = None,
) -> tuple[str, list[ConsultedResource]]:
    """Exécute le graphe de l'agent helper avec l'historique de conversation. Renvoie (réponse,
    ressources consultées/créées). Si ``model`` est fourni, il surcharge le modèle par défaut."""
    graph = build_helper_graph()
    initial_state: HelperState = {
        "messages": conversation_history,
        "tools": tools,
        "iteration": 0,
        "on_event": on_event,
        "model": model,
    }
    final_state = graph.invoke(initial_state)
    answer = final_state.get("final_answer", "")
    if not answer:
        last_msg = final_state.get("messages", [{}])[-1]
        answer = last_msg.get("content", "Aucune réponse produite.")
    resources = tools.consulted_resources()
    logger.info(
        "Helper agent completed in %d iterations, answer length: %d, resources: %d",
        final_state.get("iteration", 0),
        len(answer),
        len(resources),
    )
    return answer, resources
