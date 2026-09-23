"""Outils disponibles pour l'agent LangGraph.

Chaque outil est une fonction qui prend des paramètres simples et renvoie
une chaîne de texte (ou un dict sérialisable) que le LLM peut interpréter.
Les outils accèdent aux données du dossier via l'index BM25 et les
prédictions déjà déposées (classification + extraction).

Outils :
- search_documents : recherche BM25 dans le contenu des pages
- read_page : contenu complet d'une page spécifique
- view_classifications : toutes les classifications de pages (labels)
- view_entities : toutes les entités extraites

Suivi des sources : chaque appel d'outil qui consulte un document ou une
page enregistre une "source consultée" (page_id, document_id, excerpt).
Le graphe de chat récupère ces sources pour les déposer sur le message
assistant final via MessageSource.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from app.bm25 import BM25Index, build_index_from_dossier

logger = logging.getLogger(__name__)


@dataclass
class ConsultedSource:
    """Source consultée par l'agent pendant l'exécution. Mappée vers
    MessageSource lors du dépôt du message assistant final."""

    dossier_document_id: str | None = None
    page_ids: list[str] = field(default_factory=list)
    excerpt: str | None = None


class AgentTools:
    """Conteneur d'outils pour l'agent LangGraph. Construit à partir du
    dossier complet (avec pages et prédictions) récupéré via l'API interne.

    Le suivi des sources (_consulted_sources) accumule les pages/documents
    consultés pendant l'exécution. Le graphe de chat les récupère via
    consulted_sources() pour les déposer sur le message assistant final."""

    def __init__(self, dossier: dict) -> None:
        self._dossier = dossier
        self._index: BM25Index = build_index_from_dossier(dossier)
        self._pages_by_id: dict[str, dict] = {}
        self._pages_by_number: dict[int, dict] = {}
        self._documents_by_id: dict[str, dict] = {}
        for document in dossier.get("documents", []):
            self._documents_by_id[document["id"]] = document
            for page in document.get("pages", []):
                page["_document_name"] = document.get("name", "")
                page["_document_id"] = document.get("id")
                self._pages_by_id[page["id"]] = page
                self._pages_by_number[page["page_number"]] = page
        self._consulted_sources: list[ConsultedSource] = []

    # --- Suivi des sources ---

    def consulted_sources(self) -> list[ConsultedSource]:
        """Renvoie la liste des sources consultées pendant l'exécution.
        Dédupliquée par (document_id, page_ids) pour éviter les doublons."""
        seen: set[str] = set()
        result: list[ConsultedSource] = []
        for src in self._consulted_sources:
            key = f"{src.dossier_document_id}:{'|'.join(sorted(src.page_ids))}"
            if key not in seen:
                seen.add(key)
                result.append(src)
        return result

    def _record_source(
        self, *, page_id: str | None = None, excerpt: str | None = None
    ) -> None:
        """Enregistre une source consultée (page d'un document)."""
        if page_id is None:
            return
        page = self._pages_by_id.get(page_id)
        if page is None:
            return
        self._consulted_sources.append(
            ConsultedSource(
                dossier_document_id=page.get("_document_id"),
                page_ids=[page_id],
                excerpt=excerpt,
            )
        )

    # --- Outils exposés au LLM ---

    def search_documents(self, query: str) -> str:
        """Recherche dans le contenu des pages du dossier. Renvoie les
        pages les plus pertinentes avec un extrait du texte."""
        results = self._index.search(query)
        if not results:
            return "Aucun résultat trouvé pour cette recherche."
        lines = [f"{len(results)} résultat(s) trouvé(s) :\n"]
        for r in results:
            lines.append(
                f"📄 Page {r.page_number} ({r.document_name}) "
                f"[score: {r.score:.2f}]\n"
                f"   {r.excerpt}\n"
            )
            # Enregistre chaque page trouvée comme source consultée.
            self._record_source(page_id=r.page_id, excerpt=r.excerpt)
        return "\n".join(lines)

    def read_page(self, page_number: int) -> str:
        """Lit le contenu complet d'une page spécifique par son numéro."""
        page = self._pages_by_number.get(page_number)
        if page is None:
            return f"Page {page_number} introuvable."
        doc_name = page.get("_document_name", "")
        content = page.get("content") or "(page vide)"
        # Enregistre la page lue comme source consultée, avec un extrait
        # (les 200 premiers caractères) pour le contexte.
        excerpt = (content[:200] + "...") if len(content) > 200 else content
        self._record_source(page_id=page["id"], excerpt=excerpt)
        return f"📄 Page {page_number} ({doc_name})\n\n{content}"

    def view_classifications(self) -> str:
        """Liste toutes les classifications de pages (labels prédits)."""
        entries: list[str] = []
        for page in self._pages_by_id.values():
            for pred in page.get("predictions", []):
                if pred.get("kind") == "label":
                    entries.append(
                        f"  Page {page['page_number']}: "
                        f"{pred['name']} (confiance: {pred.get('confidence', '?')})"
                    )
        if not entries:
            return "Aucune classification disponible."
        return "Classifications des pages :\n" + "\n".join(entries)

    def view_entities(self) -> str:
        """Liste toutes les entités extraites des pages."""
        seen: dict[str, dict] = {}
        for page in self._pages_by_id.values():
            for pred in page.get("predictions", []):
                if pred.get("kind") == "entity":
                    key = pred["name"]
                    if key not in seen:
                        seen[key] = {
                            "name": pred["name"],
                            "value": pred["value"],
                            "confidence": pred.get("confidence"),
                            "pages": [page["page_number"]],
                        }
                    else:
                        if page["page_number"] not in seen[key]["pages"]:
                            seen[key]["pages"].append(page["page_number"])
        if not seen:
            return "Aucune entité extraite."
        lines = ["Entités extraites :"]
        for entity in seen.values():
            pages_str = ", ".join(str(p) for p in entity["pages"])
            lines.append(
                f"  {entity['name']}: {entity['value']} "
                f"(confiance: {entity.get('confidence', '?')}, pages: {pages_str})"
            )
        return "\n".join(lines)

    # --- Métadonnées pour le LLM ---

    def tool_definitions(self) -> list[dict[str, Any]]:
        """Renvoie les définitions d'outils au format attendu par l'API
        OpenAI (function calling)."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_documents",
                    "description": (
                        "Recherche dans le contenu des pages du dossier. "
                        "Utilise cette recherche pour trouver des informations "
                        "pertinentes (noms, dates, adresses, montants...)."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Requête de recherche",
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_page",
                    "description": (
                        "Lit le contenu complet d'une page par son numéro. "
                        "Utilise cet outil après une recherche pour lire le "
                        "détail d'une page pertinente."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "page_number": {
                                "type": "integer",
                                "description": "Numéro de la page à lire",
                            }
                        },
                        "required": ["page_number"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "view_classifications",
                    "description": (
                        "Liste toutes les classifications de pages (types de "
                        "documents identifiés). Utilise cet outil pour voir "
                        "quels documents sont dans le dossier."
                    ),
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "view_entities",
                    "description": (
                        "Liste toutes les entités extraites (noms, dates, "
                        "adresses, montants...). Utilise cet outil pour voir "
                        "les informations déjà extraites du dossier."
                    ),
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

    def dispatch_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Exécute un outil par son nom et renvoie le résultat."""
        if name == "search_documents":
            return self.search_documents(arguments.get("query", ""))
        if name == "read_page":
            return self.read_page(arguments.get("page_number", 0))
        if name == "view_classifications":
            return self.view_classifications()
        if name == "view_entities":
            return self.view_entities()
        return f"Outil '{name}' inconnu."
