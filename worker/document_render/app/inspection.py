"""Contrôle d'un modèle ODT à l'import (issue #148, suite de #146).

Un modèle peut être **valide** (syntaxe, champs) et pourtant produire un PDF différent de ce que voit son auteur :
LibreOffice remplace **sans prévenir** une police absente de l'image. Ce module relève ce qui risque de
surprendre, **sans rien bloquer** (ce sont des avertissements pour l'administrateur) :

- **polices** utilisées par le modèle et absentes de l'image (remplacées par une autre) ;
- **champs natifs LibreOffice** (champs utilisateur, variables, champs de saisie) : l'application ne les
  remplit pas, seule la syntaxe ``{{ nom }}`` est prise en charge ;
- **images** du modèle : conservées telles quelles (un logo), mais une image qui change selon le dossier
  (signature) n'est pas prise en charge.

Les placeholders dans un cadre, un en-tête ou un pied de page sont, eux, remplis comme ailleurs.
"""

import io
import subprocess
import zipfile
from dataclasses import asdict, dataclass

from lxml import etree

from app.config import settings

NS = {
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
}
PARTS = ("content.xml", "styles.xml")

# Polices d'usage courant et leur équivalent **métriquement compatible** (mêmes largeurs de caractères : la mise
# en page est conservée). Installées dans l'image : Liberation, Carlito, Caladea.
METRIC_COMPATIBLE = {
    "arial": "liberation sans",
    "helvetica": "liberation sans",
    "times new roman": "liberation serif",
    "times": "liberation serif",
    "courier new": "liberation mono",
    "courier": "liberation mono",
    "calibri": "carlito",
    "cambria": "caladea",
}
GENERIC_FAMILIES = {"serif", "sans-serif", "sans", "monospace", "cursive", "fantasy", "system-ui"}

# Champs natifs LibreOffice que l'application ne remplit pas (hors champs calculés par LibreOffice lui-même :
# date, numéro de page… qui fonctionnent à la conversion).
NATIVE_FIELDS = {
    "user-field-get": "champ utilisateur",
    "user-field-decl": "champ utilisateur",
    "variable-set": "variable",
    "variable-get": "variable",
    "variable-input": "variable de saisie",
    "text-input": "champ de saisie",
    "placeholder": "champ de substitution",
    "conditional-text": "texte conditionnel",
}


@dataclass
class FontReport:
    name: str
    # « installed » : présente ; « compatible » : remplacée par une police de mêmes métriques ; « substituted » :
    # remplacée par une autre (la mise en page change) ; « unknown » : non vérifiable (fontconfig absent).
    status: str
    replaced_by: str | None = None


@dataclass
class Warning:  # noqa: A001 - nom du domaine : un avertissement à l'import
    code: str
    level: str  # « warning » ou « info »
    message: str


def _roots(odt: bytes) -> list[etree._Element]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(odt))
        return [etree.fromstring(archive.read(name)) for name in PARTS if name in archive.namelist()]
    except (zipfile.BadZipFile, etree.XMLSyntaxError):
        return []


def used_fonts(odt: bytes) -> list[str]:
    """Familles de polices **référencées** par les styles du modèle (pas toutes les polices déclarées, dont
    beaucoup sont des valeurs par défaut jamais utilisées pour le texte latin), dans l'ordre d'apparition."""
    declared: dict[str, str] = {}
    referenced: list[str] = []
    for root in _roots(odt):
        for face in root.iterfind(".//style:font-face", NS):
            family = face.get(f"{{{NS['svg']}}}font-family")
            if family:
                declared[face.get(f"{{{NS['style']}}}name", family)] = family
        for props in root.iterfind(".//style:text-properties", NS):
            for attribute in (f"{{{NS['style']}}}font-name", f"{{{NS['fo']}}}font-family"):
                value = props.get(attribute)
                if value:
                    referenced.append(value)
    families: list[str] = []
    for value in referenced:
        for family in declared.get(value, value).split(","):
            family = family.strip().strip("'\"").strip()
            if family and family.lower() not in GENERIC_FAMILIES and family not in families:
                families.append(family)
    return families


def check_font(family: str) -> FontReport:
    """Est-ce que l'image a cette police ? Demande à fontconfig, qui répond par la police la plus proche."""
    try:
        result = subprocess.run(
            [settings.FC_MATCH_BINARY, family, "family"], capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return FontReport(family, "unknown")
    matched = [name.strip() for name in result.stdout.strip().split(",") if name.strip()]
    if result.returncode != 0 or not matched:
        return FontReport(family, "unknown")
    if family.casefold() in (name.casefold() for name in matched):
        return FontReport(family, "installed")
    if METRIC_COMPATIBLE.get(family.casefold()) in (name.casefold() for name in matched):
        return FontReport(family, "compatible", matched[0])
    return FontReport(family, "substituted", matched[0])


def native_fields(odt: bytes) -> dict[str, int]:
    """Champs natifs LibreOffice présents (type → nombre) : l'application ne les remplit pas."""
    found: dict[str, int] = {}
    for root in _roots(odt):
        for tag, label in NATIVE_FIELDS.items():
            count = len(root.findall(f".//text:{tag}", NS))
            if count:
                found[label] = found.get(label, 0) + count
    return found


def image_count(odt: bytes) -> int:
    return sum(len(root.findall(".//draw:image", NS)) for root in _roots(odt))


def inspect(odt: bytes) -> dict:
    """Rapport de contrôle d'un modèle : polices et avertissements (aucun n'est bloquant)."""
    fonts = [check_font(family) for family in used_fonts(odt)]
    warnings: list[Warning] = []
    for font in fonts:
        if font.status == "substituted":
            warnings.append(
                Warning(
                    "font_substituted",
                    "warning",
                    f"La police « {font.name} » n'est pas installée dans l'image : LibreOffice la remplacera par "
                    f"« {font.replaced_by} » et la mise en page du PDF différera de celle de l'auteur.",
                )
            )
    if fonts and all(font.status == "unknown" for font in fonts):
        warnings.append(
            Warning("fonts_unchecked", "info", "Les polices du modèle n'ont pas pu être vérifiées (fontconfig absent).")
        )
    for label, count in sorted(native_fields(odt).items()):
        warnings.append(
            Warning(
                "native_field",
                "warning",
                f"Le modèle contient {count} {label}(s) natif(s) de LibreOffice : l'application ne les remplit pas. "
                "Utilisez la syntaxe {{ nom }}.",
            )
        )
    images = image_count(odt)
    if images:
        warnings.append(
            Warning(
                "images",
                "info",
                f"Le modèle contient {images} image(s) : elles sont conservées telles quelles. Une image qui change "
                "selon le dossier (signature) n'est pas prise en charge.",
            )
        )
    return {"fonts": [asdict(f) for f in fonts], "warnings": [asdict(w) for w in warnings]}
