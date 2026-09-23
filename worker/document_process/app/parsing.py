from liteparse import LiteParse
from liteparse.types import ParseResult

from app.config import settings


def parse_file(data: bytes) -> ParseResult:
    """Extrait le texte et une capture par page d'un PDF/Office/image. OCR
    Tesseract (français par défaut) pour les pages scannées."""
    parser = LiteParse(
        output_format="json",
        ocr_enabled=True,
        ocr_language=settings.OCR_LANGUAGE,
        tessdata_path=settings.TESSDATA_PATH,
        extract_screenshots=True,
    )
    return parser.parse(data)
