"""Outils disponibles pour l'agent helper LangGraph (issue #50).

Sur le modèle de app/tools.py (chat par dossier), mais chaque outil parle
au backend via /api/internal/agent/* (app.api_client) plutôt qu'à un
dossier déjà chargé en mémoire : l'agent helper n'est scopé à aucun
dossier/analyse au départ, il les recherche/crée au fil de la conversation.

Pas de tool d'upload de fichiers ici (contrairement au serveur MCP
helper_server.py côté backend) : un LLM ne peut pas produire le contenu
binaire d'un vrai document depuis un message texte. L'ajout de fichiers
dans la modal (Phase 8, frontend) passera par une action d'upload dédiée,
pas par un tool du graphe de chat.

Suivi des ressources consultées : chaque outil qui lit/crée un dossier ou
une analyse enregistre une "ressource consultée" (dossier_id/analyse_id +
un court extrait). Le graphe les récupère pour les déposer comme
AgentMessageSource sur le message assistant final - c'est ce qui permet au
frontend d'afficher un lien direct vers le dossier trouvé/créé.
"""

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app import api_client

logger = logging.getLogger(__name__)


@dataclass
class ConsultedResource:
    """Ressource consultée par l'agent pendant l'exécution. Mappée vers
    AgentMessageSource lors du dépôt du message assistant final."""

    dossier_id: str | None = None
    analyse_id: str | None = None
    excerpt: str | None = None


class HelperTools:
    """Conteneur d'outils pour l'agent LangGraph helper. Chaque appel passe
    par l'API interne (client HTTP authentifié, voir app.api_client) -
    contrairement à AgentTools (chat par dossier), il n'y a pas de dossier
    déjà chargé en mémoire à interroger localement."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client
        self._consulted: list[ConsultedResource] = []

    # --- Suivi des ressources ---

    def consulted_resources(self) -> list[ConsultedResource]:
        """Renvoie les ressources consultées pendant l'exécution, dédupliquées
        par (dossier_id, analyse_id)."""
        seen: set[tuple[str | None, str | None]] = set()
        result: list[ConsultedResource] = []
        for res in self._consulted:
            key = (res.dossier_id, res.analyse_id)
            if key not in seen:
                seen.add(key)
                result.append(res)
        return result

    def _record(
        self, *, dossier_id: str | None = None, analyse_id: str | None = None, excerpt: str | None = None
    ) -> None:
        self._consulted.append(ConsultedResource(dossier_id=dossier_id, analyse_id=analyse_id, excerpt=excerpt))

    # --- Outils exposés au LLM : analyses ---

    def list_analyses(self, page: int = 1, page_size: int = 20) -> str:
        """Liste les analyses persistantes de la plateforme."""
        result = api_client.list_agent_analyses(self._client, page=page, page_size=page_size)
        return self._format_analyses(result)

    def search_analyses(self, q: str) -> str:
        """Recherche des analyses persistantes par nom."""
        result = api_client.list_agent_analyses(self._client, q=q)
        return self._format_analyses(result)

    def _format_analyses(self, result: dict) -> str:
        items = result.get("items", [])
        if not items:
            return "Aucune analyse trouvée."
        lines = [f"{result['total']} analyse(s) :"]
        for a in items:
            lines.append(f"- {a['name']} (id: {a['id']}) - {a['agent_count']} agent(s), {a['description']}")
            self._record(analyse_id=a["id"], excerpt=a["name"])
        return "\n".join(lines)

    def get_analysis(self, analyse_id: str) -> str:
        """Détail complet d'une analyse (labels, entités, prompts)."""
        try:
            analyse = api_client.get_agent_analysis(self._client, analyse_id)
        except httpx.HTTPStatusError as error:
            return _error_message(error)
        labels = ", ".join(label["name"] for label in analyse["classification"]["labels"]) or "(aucun)"
        entities = ", ".join(entity["name"] for entity in analyse["extraction"]["entities"]) or "(aucune)"
        self._record(analyse_id=analyse["id"], excerpt=analyse["name"])
        return (
            f"Analyse « {analyse['name']} » (id: {analyse['id']})\n"
            f"Description : {analyse['description']}\n"
            f"Labels de classification : {labels}\n"
            f"Entités d'extraction : {entities}"
        )

    def create_analysis(self, name: str, description: str) -> str:
        """Crée une analyse persistante (nom + description) - la classification, l'extraction et
        les agents se configurent ensuite via la plateforme."""
        analyse = api_client.create_agent_analysis(self._client, name=name, description=description)
        self._record(analyse_id=analyse["id"], excerpt=analyse["name"])
        return f"Analyse « {analyse['name']} » créée (id: {analyse['id']})."

    # --- Outils exposés au LLM : dossiers ---

    def list_dossiers(self, page: int = 1, page_size: int = 20) -> str:
        """Liste les dossiers persistants de la plateforme."""
        result = api_client.list_agent_dossiers(self._client, page=page, page_size=page_size)
        items = result.get("items", [])
        if not items:
            return "Aucun dossier trouvé."
        lines = [f"{result['total']} dossier(s) :"]
        for d in items:
            lines.append(f"- {d['name']} (id: {d['id']}) - statut : {d['status']}")
            self._record(dossier_id=d["id"], excerpt=d["name"])
        return "\n".join(lines)

    def get_dossier(self, dossier_id: str) -> str:
        """Détail d'un dossier : documents, statut, résultats une fois le pipeline terminé."""
        try:
            dossier = api_client.get_agent_dossier(self._client, dossier_id)
        except httpx.HTTPStatusError as error:
            return _error_message(error)
        return self._format_dossier(dossier)

    def create_dossier(self, name: str, analyse_id: str) -> str:
        """Crée un dossier persistant, associé à une analyse existante."""
        try:
            dossier = api_client.create_agent_dossier(self._client, name=name, analyse_id=analyse_id)
        except httpx.HTTPStatusError as error:
            return _error_message(error)
        self._record(dossier_id=dossier["id"], excerpt=dossier["name"])
        return f"Dossier « {dossier['name']} » créé (id: {dossier['id']}), sans document pour l'instant."

    def run_dossier(self, dossier_id: str) -> str:
        """Lance le pipeline (classification, extraction, agents) sur un dossier déjà créé, avec
        ses fichiers déjà ajoutés. Démarre en arrière-plan, revient immédiatement."""
        try:
            dossier = api_client.launch_agent_dossier(self._client, dossier_id)
        except httpx.HTTPStatusError as error:
            return _error_message(error)
        self._record(dossier_id=dossier["id"], excerpt=dossier["name"])
        return f"Pipeline lancé sur « {dossier['name']} » (statut : {dossier['status']})."

    def get_dossier_results(self, dossier_id: str) -> str:
        """Résultats d'un dossier (statut, synthèses des agents) - à appeler en boucle après
        run_dossier jusqu'à un statut terminal."""
        return self.get_dossier(dossier_id)

    def _format_dossier(self, dossier: dict) -> str:
        self._record(dossier_id=dossier["id"], excerpt=dossier["name"])
        lines = [
            f"Dossier « {dossier['name']} » (id: {dossier['id']})",
            f"Statut : {dossier['status']}",
            f"Documents : {len(dossier['documents'])}",
        ]
        syntheses = [
            step for step in dossier.get("execution_steps", []) if step.get("kind") == "agent" and step.get("output")
        ]
        if syntheses:
            lines.append("\nSynthèses des agents :")
            for step in syntheses:
                lines.append(f"\n[{step['label']}]\n{step['output']}")
        return "\n".join(lines)

    # --- Métadonnées pour le LLM ---

    def tool_definitions(self) -> list[dict[str, Any]]:
        """Renvoie les définitions d'outils au format attendu par l'API OpenAI (function calling)."""
        return [
            _tool_def(
                "list_analyses",
                "Liste les analyses persistantes de la plateforme (classification, extraction, agents).",
                {},
            ),
            _tool_def(
                "search_analyses",
                "Recherche des analyses persistantes par nom. Utilise cet outil avant d'en créer une "
                "nouvelle, pour proposer de réutiliser une analyse existante si pertinent.",
                {"q": {"type": "string", "description": "Terme de recherche"}},
                required=["q"],
            ),
            _tool_def(
                "get_analysis",
                "Détail complet d'une analyse (labels, entités, prompts).",
                {"analyse_id": {"type": "string", "description": "Identifiant de l'analyse"}},
                required=["analyse_id"],
            ),
            _tool_def(
                "create_analysis",
                "Crée une analyse persistante (nom + description).",
                {
                    "name": {"type": "string", "description": "Nom de l'analyse"},
                    "description": {"type": "string", "description": "Objectif métier de l'analyse"},
                },
                required=["name", "description"],
            ),
            _tool_def(
                "list_dossiers",
                "Liste les dossiers persistants de la plateforme.",
                {},
            ),
            _tool_def(
                "get_dossier",
                "Détail d'un dossier : documents, statut, résultats une fois le pipeline terminé.",
                {"dossier_id": {"type": "string", "description": "Identifiant du dossier"}},
                required=["dossier_id"],
            ),
            _tool_def(
                "create_dossier",
                "Crée un dossier persistant, associé à une analyse existante.",
                {
                    "name": {"type": "string", "description": "Nom du dossier"},
                    "analyse_id": {"type": "string", "description": "Identifiant de l'analyse associée"},
                },
                required=["name", "analyse_id"],
            ),
            _tool_def(
                "run_dossier",
                "Lance le pipeline (classification, extraction, agents) sur un dossier - démarre en "
                "arrière-plan, revient immédiatement.",
                {"dossier_id": {"type": "string", "description": "Identifiant du dossier"}},
                required=["dossier_id"],
            ),
            _tool_def(
                "get_dossier_results",
                "Résultats d'un dossier (statut, synthèses des agents) - à appeler après run_dossier "
                "jusqu'à un statut terminal.",
                {"dossier_id": {"type": "string", "description": "Identifiant du dossier"}},
                required=["dossier_id"],
            ),
        ]

    def dispatch_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Exécute un outil par son nom et renvoie le résultat."""
        if name == "list_analyses":
            return self.list_analyses()
        if name == "search_analyses":
            return self.search_analyses(arguments.get("q", ""))
        if name == "get_analysis":
            return self.get_analysis(arguments.get("analyse_id", ""))
        if name == "create_analysis":
            return self.create_analysis(arguments.get("name", ""), arguments.get("description", ""))
        if name == "list_dossiers":
            return self.list_dossiers()
        if name == "get_dossier":
            return self.get_dossier(arguments.get("dossier_id", ""))
        if name == "create_dossier":
            return self.create_dossier(arguments.get("name", ""), arguments.get("analyse_id", ""))
        if name == "run_dossier":
            return self.run_dossier(arguments.get("dossier_id", ""))
        if name == "get_dossier_results":
            return self.get_dossier_results(arguments.get("dossier_id", ""))
        return f"Outil '{name}' inconnu."


def _tool_def(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required or []},
        },
    }


def _error_message(error: httpx.HTTPStatusError) -> str:
    try:
        detail = error.response.json().get("detail", error.response.text)
    except Exception:
        detail = error.response.text
    return f"Erreur : {detail}"
