from liteparse import LiteParse
from liteparse.types import ParseResult

from app.config import settings


def parse_file(data: bytes) -> ParseResult:
    """Extrait le texte, les blocs de mise en page (avec bbox) et une
    capture par page d'un PDF/Office/image. OCR Tesseract (français par
    défaut) pour les pages scannées. Les bbox des blocs sont ce qu'une
    future étape de classification/extraction d'entités pourra référencer
    pour localiser sa réponse sur la page (voir prediction_bounding_boxes
    côté backend)."""
    parser = LiteParse(
        output_format="json",
        ocr_enabled=True,
        ocr_language=settings.OCR_LANGUAGE,
        tessdata_path=settings.TESSDATA_PATH,
        extract_screenshots=True,
        extract_blocks=True,
    )
    return parser.parse(data)
