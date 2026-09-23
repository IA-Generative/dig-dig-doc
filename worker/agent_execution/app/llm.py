"""Client OpenAI pour la classification et l'extraction d'entités.

Deux usages distincts :
- VLM (vision-language model) : décrit la capture d'une page en texte, pour
  enrichir le contexte de classification au-delà du seul texte extrait par
  OCR. Le VLM reçoit l'image + un prompt court, et renvoie une description
  textuelle structurée.
- LLM (texte) : classification documentaire et extraction d'entités en
  structured output (JSON schema via response_format), pour garantir un
  résultat cohérent avec les définitions de l'analyse (labels/entités).
"""

import base64
import logging

from openai import OpenAI
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)


def _client() -> OpenAI:
    if not settings.is_configured:
        raise RuntimeError(
            "OPENAI_API_KEY et OPENAI_API_BASE_URL doivent être configurés "
            "pour utiliser le worker agent_execution."
        )
    return OpenAI(
        api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_API_BASE_URL
    )


# ---------------------------------------------------------------------------
# Structured output models
# ---------------------------------------------------------------------------


class LabelPrediction(BaseModel):
    """Résultat de classification pour une page : un label parmi ceux
    définis dans l'analyse, avec un niveau de confiance."""

    label_name: str = Field(
        description="Nom exact du label choisi parmi les définitions fournies"
    )
    confidence: float = Field(
        description="Score de confiance entre 0 et 1", ge=0.0, le=1.0
    )
    reasoning: str = Field(
        default="", description="Brève justification du choix (optionnel)"
    )


class ClassificationResult(BaseModel):
    """Résultat de classification pour une page : un seul label (la
    classification est mono-label par page)."""

    prediction: LabelPrediction


class EntityValue(BaseModel):
    """Une entité extraite d'une ou plusieurs pages."""

    entity_name: str = Field(
        description="Nom exact de l'entité parmi les définitions fournies"
    )
    value: str = Field(description="Valeur extraite pour cette entité")
    confidence: float = Field(
        description="Score de confiance entre 0 et 1", ge=0.0, le=1.0
    )
    page_numbers: list[int] = Field(
        default_factory=list,
        description="Numéros des pages (1-indexed) où cette entité apparaît",
    )
    reasoning: str = Field(default="", description="Brève justification (optionnel)")


class ExtractionResult(BaseModel):
    """Résultat d'extraction d'entités pour un batch de pages."""

    entities: list[EntityValue] = Field(
        default_factory=list, description="Entités extraites du batch"
    )


# ---------------------------------------------------------------------------
# VLM : description d'image
# ---------------------------------------------------------------------------

_VLM_PROMPT = (
    "Décris cette page de document de manière structurée et factuelle. "
    "Identifie : le type de document (CNI, passeport, facture, contrat...), "
    "les éléments visibles (titres, tableaux, signatures, tampons, photos), "
    "et toute information pertinente pour sa classification. "
    "Sois concis mais précis."
)


def describe_page_image(image_bytes: bytes) -> str:
    """Demande au VLM de décrire la capture d'une page. Le texte renvoyé
    est combiné avec le texte OCR de la page pour alimenter la
    classification (le LLM texte a ainsi à la fois le contenu lu et ce que
    le VLM a vu)."""
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    response = _client().chat.completions.create(
        model=settings.VLM_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _VLM_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            }
        ],
        max_tokens=500,
        temperature=0.1,
    )
    return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# LLM : classification (structured output)
# ---------------------------------------------------------------------------


def classify_page(
    *,
    page_text: str,
    image_description: str,
    label_definitions: list[dict],
    classification_prompt: str,
) -> ClassificationResult:
    """Classifie une page en utilisant le texte OCR + la description VLM.
    Renvoie un résultat structuré (ClassificationResult) garantissant que
    le label choisi existe parmi les définitions fournies."""
    labels_desc = "\n".join(
        f"- {label['name']}: {label['definition']}" for label in label_definitions
    )
    system = (
        f"{classification_prompt}\n\n"
        f"Tu es un assistant de classification documentaire. "
        f"Choisis UN seul label parmi les suivants :\n{labels_desc}\n\n"
        f"Réponds uniquement avec le JSON demandé."
    )
    user = (
        f"--- Texte extrait de la page (OCR) ---\n{page_text or '(vide)'}\n\n"
        f"--- Description visuelle de la page (VLM) ---\n{image_description or '(indisponible)'}\n\n"
        f"Quel label correspond le mieux à cette page ?"
    )
    response = _client().beta.chat.completions.parse(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format=ClassificationResult,
        temperature=0.1,
    )
    return response.choices[0].message.parsed


# ---------------------------------------------------------------------------
# LLM : extraction d'entités (structured output, batch de pages)
# ---------------------------------------------------------------------------


def extract_entities_batch(
    *,
    pages: list[dict],
    entity_definitions: list[dict],
    extraction_prompt: str,
) -> ExtractionResult:
    """Extrait les entités d'un batch de pages. Chaque page est un dict avec
    `page_number` et `content`. Renvoie un résultat structuré
    (ExtractionResult) garantissant que chaque entité extraite correspond à
    une définition fournie."""
    entities_desc = "\n".join(
        f"- {entity['name']} (type: {entity['type']}): {entity['definition']}"
        for entity in entity_definitions
    )
    system = (
        f"{extraction_prompt}\n\n"
        f"Tu es un assistant d'extraction d'entités. "
        f"Extrais les valeurs pour les entités suivantes :\n{entities_desc}\n\n"
        f"Pour chaque entité trouvée, indique sur quelles pages (par numéro) "
        f"elle apparaît. Si une entité n'est pas présente, ne l'inclus pas. "
        f"Réponds uniquement avec le JSON demandé."
    )
    pages_text = "\n\n".join(
        f"--- Page {page['page_number']} ---\n{page['content'] or '(vide)'}"
        for page in pages
    )
    response = _client().beta.chat.completions.parse(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": pages_text},
        ],
        response_format=ExtractionResult,
        temperature=0.1,
    )
    return response.choices[0].message.parsed
