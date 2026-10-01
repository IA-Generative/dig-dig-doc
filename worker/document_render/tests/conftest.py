import io
import zipfile

import pytest

NS = (
    'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
    'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
    'xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" '
    'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
    'xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"'
)
MANIFEST = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3">'
    '<manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/>'
    '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
    '<manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>'
    "</manifest:manifest>"
)
STYLES_AUTOMATIC = (
    '<office:automatic-styles><style:style style:name="T1" style:family="text">'
    '<style:text-properties fo:font-weight="bold"/></style:style>'
    '<style:style style:name="T2" style:family="text"><style:text-properties fo:font-style="italic"/>'
    "</style:style></office:automatic-styles>"
)


def make_odt(body: str, *, header: str = "", extra: dict[str, bytes] | None = None) -> bytes:
    """Un ODT minimal mais valide : ``body`` est le contenu de ``office:text`` ; ``header`` celui de
    l'en-tête de page (dans ``styles.xml``) ; ``extra`` des fichiers supplémentaires (images…)."""
    content = (
        f'<?xml version="1.0" encoding="UTF-8"?><office:document-content {NS} office:version="1.3">'
        f"{STYLES_AUTOMATIC}<office:body><office:text>{body}</office:text></office:body></office:document-content>"
    )
    styles = (
        f'<?xml version="1.0" encoding="UTF-8"?><office:document-styles {NS} office:version="1.3">'
        f'<office:master-styles><style:master-page style:name="Standard"><style:header>{header}</style:header>'
        "</style:master-page></office:master-styles></office:document-styles>"
    )
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr(zipfile.ZipInfo("mimetype"), "application/vnd.oasis.opendocument.text", zipfile.ZIP_STORED)
        archive.writestr("META-INF/manifest.xml", MANIFEST)
        archive.writestr("content.xml", content)
        archive.writestr("styles.xml", styles)
        for name, data in (extra or {}).items():
            archive.writestr(name, data)
    return out.getvalue()


def read_part(odt: bytes, name: str = "content.xml") -> str:
    return zipfile.ZipFile(io.BytesIO(odt)).read(name).decode("utf-8")


@pytest.fixture
def odt():
    return make_odt
