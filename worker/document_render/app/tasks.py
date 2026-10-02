"""Tâches du worker de rendu de documents (issue #146).

Aucune ne touche à l'analyse ni à la base : elles lisent un modèle dans S3, le remplissent par des
valeurs déjà décidées, et déposent le résultat dans S3. Qui décide des valeurs (agent, instructeur)
et où est enregistré le document, c'est l'affaire du backend (#140, #143)."""

import logging

from app import inspection, odt_template
from app.celery_app import celery_app
from app.pdf import odt_to_pdf
from app.storage import storage

logger = logging.getLogger(__name__)

ODT_TYPE = "application/vnd.oasis.opendocument.text"


@celery_app.task(name="app.tasks.extract_template_fields")
def extract_template_fields(template_key: str) -> list[str]:
    """Champs utilisés par un modèle : le backend les compare à la définition de champs (#138).
    Un modèle invalide lève OdtTemplateError (visible dans le résultat de la tâche)."""
    return odt_template.extract_fields(storage.get_object(template_key))


@celery_app.task(name="app.tasks.inspect_template")
def inspect_template(template_key: str) -> dict:
    """Contrôle d'un modèle à l'import (issue #148) : ses champs (comme ``extract_template_fields``), les polices
    qu'il utilise et ce qui risque de surprendre. Un modèle invalide lève OdtTemplateError ; les avertissements
    ne bloquent rien."""
    odt = storage.get_object(template_key)
    return {"fields": odt_template.extract_fields(odt), **inspection.inspect(odt)}


@celery_app.task(name="app.tasks.render_document")
def render_document(template_key: str, values: dict, output_prefix: str, with_pdf: bool = True) -> dict:
    """Remplit le modèle, dépose ``<prefix>.odt`` (et ``<prefix>.pdf``) dans S3 et renvoie leurs clés."""
    odt = odt_template.render(storage.get_object(template_key), values)
    result = {"odt_key": f"{output_prefix}.odt"}
    storage.put_object(result["odt_key"], odt, ODT_TYPE)
    if with_pdf:
        result["pdf_key"] = f"{output_prefix}.pdf"
        storage.put_object(result["pdf_key"], odt_to_pdf(odt), "application/pdf")
    logger.info("Document rendered: %s", result)
    return result


@celery_app.task(name="app.tasks.render_preview")
def render_preview(template_key: str, values: dict, output_key: str) -> str:
    """Aperçu : le modèle rempli, en PDF uniquement (rien d'autre n'est conservé)."""
    pdf = odt_to_pdf(odt_template.render(storage.get_object(template_key), values))
    storage.put_object(output_key, pdf, "application/pdf")
    return output_key
