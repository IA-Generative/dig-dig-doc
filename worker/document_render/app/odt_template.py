"""Remplissage d'un modèle ODT (issue #146, parent #107).

Un modèle ODT contient des **placeholders** ``{{ champ }}`` et des **blocs** (listes,
lignes de tableau) écrits dans LibreOffice. Ce module les remplit par des valeurs de
façon **déterministe**, sans LibreOffice (qui ne sert qu'à produire le PDF, voir
``pdf.py``) : seuls ``content.xml`` et ``styles.xml`` (en-têtes et pieds de page) sont
réécrits, le reste du fichier (styles, images, mise en page) est recopié tel quel.

Syntaxe (moteur Jinja, en mode bac à sable) :

- ``{{ nom }}``, ``{{ e.valeur }}`` : valeur d'un champ ou d'un attribut ;
- ``{% if x %}…{% endif %}`` : condition, dans un même paragraphe ;
- **blocs à portée structurelle**, chacun dans un élément **dédié** (qui ne contient
  que la balise) : ``{%p for e in entites %}`` … ``{%p endfor %}`` répète des
  paragraphes ; ``{%tr for e in entites %}`` … ``{%tr endfor %}`` répète des lignes de
  tableau ; ``{%li for e in entites %}`` … ``{%li endfor %}`` répète des éléments de
  liste. Les éléments qui portent les balises sont supprimés du résultat.

Écueil traité : LibreOffice **fragmente** un placeholder en plusieurs morceaux de texte
(``text:span``) dès que la mise en forme change au milieu (correcteur orthographique,
changement de style). Avant tout traitement, chaque balise est **fusionnée** en un seul
morceau (``_merge_fragmented_tags``).
"""

import html
import io
import re
import zipfile
from collections.abc import Iterator
from typing import Any

from jinja2 import StrictUndefined, TemplateSyntaxError, meta
from jinja2.exceptions import UndefinedError
from jinja2.sandbox import SandboxedEnvironment, SecurityError
from lxml import etree

TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
TABLE = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
_T = f"{{{TEXT}}}"

# Les deux parties de l'ODT qui peuvent contenir des placeholders : le corps du
# document et les styles (en-têtes et pieds de page des pages maîtresses).
RENDERED_PARTS = ("content.xml", "styles.xml")

_TAG = re.compile(r"\{%.*?%\}|\{\{.*?\}\}|\{#.*?#\}", re.S)
_SCOPED = re.compile(r"^\s*\{%(?P<scope>p|tr|li)\s+(?P<body>.*?)\s*%\}\s*$", re.S)
_SCOPE_ANCESTOR = {"tr": f"{{{TABLE}}}table-row", "li": f"{_T}list-item"}
# Caractères interdits en XML 1.0 (une valeur qui en contient rendrait le fichier illisible).
_XML_FORBIDDEN = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")
_PARAGRAPHS = (f"{_T}p", f"{_T}h")
_XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>\n'


class OdtTemplateError(ValueError):
    """Le modèle est invalide (balise mal formée, bloc non fermé, élément de contrôle non dédié…)."""


class MissingValueError(OdtTemplateError):
    """Le modèle utilise un champ pour lequel aucune valeur n'est fournie."""


# --- Lecture et écriture de l'archive ODT ------------------------------------------------


def _read(odt: bytes) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(io.BytesIO(odt))
    except zipfile.BadZipFile as error:
        raise OdtTemplateError("Ce fichier n'est pas un document ODT valide (archive illisible)") from error


def _write(source: zipfile.ZipFile, replacements: dict[str, bytes]) -> bytes:
    """Recopie l'archive en remplaçant certaines parties. ``mimetype`` reste la première entrée,
    non compressée (exigence du format ODT)."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as target:
        for info in source.infolist():
            data = replacements.get(info.filename, source.read(info.filename))
            compress = zipfile.ZIP_STORED if info.filename == "mimetype" else zipfile.ZIP_DEFLATED
            target.writestr(zipfile.ZipInfo(info.filename, date_time=info.date_time), data, compress_type=compress)
    return out.getvalue()


def _parse(xml: bytes) -> etree._Element:
    parser = etree.XMLParser(resolve_entities=False, no_network=True, remove_blank_text=False)
    try:
        return etree.fromstring(xml, parser)
    except etree.XMLSyntaxError as error:
        raise OdtTemplateError(f"Contenu XML illisible : {error}") from error


# --- Fusion des balises fragmentées -------------------------------------------------------


def _segments(paragraph: etree._Element) -> list[tuple[etree._Element | None, str]] | None:
    """Découpe un paragraphe en (span d'origine, texte). None si le paragraphe contient autre
    chose que du texte et des ``text:span`` simples (liens, signets, champs : on n'y touche pas)."""
    parts: list[tuple[etree._Element | None, str]] = []
    if paragraph.text:
        parts.append((None, paragraph.text))
    for child in paragraph:
        if child.tag != f"{_T}span" or len(child) > 0:
            return None
        parts.append((child, child.text or ""))
        if child.tail:
            parts.append((None, child.tail))
    return parts


def _merge_fragmented_tags(paragraph: etree._Element) -> None:
    """Fusionne en un seul morceau de texte chaque balise répartie sur plusieurs spans. Le morceau
    fusionné garde le style du span où la balise commence."""
    parts = _segments(paragraph)
    if parts is None:
        return
    full = "".join(text for _, text in parts)
    if "{" not in full or not any(match for match in _TAG.finditer(full)):
        return
    # Frontières de chaque segment dans le texte complet.
    bounds: list[tuple[int, int]] = []
    pos = 0
    for _, text in parts:
        bounds.append((pos, pos + len(text)))
        pos += len(text)
    # Intervalles de segments à fusionner : ceux qu'une balise traverse.
    merge: list[tuple[int, int]] = []
    for match in _TAG.finditer(full):
        first = next(i for i, (a, b) in enumerate(bounds) if a <= match.start() < b)
        last = next(i for i, (a, b) in enumerate(bounds) if a < match.end() <= b)
        if last > first:
            merge.append((first, last))
    if not merge:
        return
    merged: list[list[int]] = []
    for first, last in sorted(merge):
        if merged and first <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], last)
        else:
            merged.append([first, last])
    # Reconstruction : chaque intervalle devient un seul segment (style du premier).
    new_parts: list[tuple[etree._Element | None, str]] = []
    index = 0
    for first, last in merged:
        new_parts.extend(parts[index:first])
        new_parts.append((parts[first][0], "".join(text for _, text in parts[first : last + 1])))
        index = last + 1
    new_parts.extend(parts[index:])
    _rebuild(paragraph, new_parts)


def _rebuild(paragraph: etree._Element, parts: list[tuple[etree._Element | None, str]]) -> None:
    for child in list(paragraph):
        paragraph.remove(child)
    paragraph.text = None
    last_span: etree._Element | None = None
    for span, text in parts:
        if span is None:
            if last_span is None:
                paragraph.text = (paragraph.text or "") + text
            else:
                last_span.tail = (last_span.tail or "") + text
        else:
            span.text = text
            span.tail = None
            paragraph.append(span)
            last_span = span


# --- Blocs à portée structurelle ({%p %}, {%tr %}, {%li %}) --------------------------------------


def _text_of(element: etree._Element) -> str:
    return "".join(element.itertext()).strip()


def _insert_text_at(element: etree._Element, text: str) -> None:
    """Place du texte brut à l'endroit de ``element`` (juste avant lui), puis retire
    ``element`` en conservant son texte de queue."""
    parent = element.getparent()
    tail = element.tail or ""
    previous = element.getprevious()
    if previous is None:
        parent.text = (parent.text or "") + text + tail
    else:
        previous.tail = (previous.tail or "") + text + tail
    parent.remove(element)


def _apply_scoped_blocks(root: etree._Element) -> None:
    """Remplace chaque élément de contrôle dédié par sa balise Jinja, placée au niveau de la
    ligne, de l'élément de liste ou du paragraphe qu'elle gouverne."""
    for paragraph in list(root.iter(*_PARAGRAPHS)):
        match = _SCOPED.match(_text_of(paragraph))
        if match is None:
            continue
        scope, body = match.group("scope"), match.group("body")
        target = paragraph
        if scope in _SCOPE_ANCESTOR:
            target = next((a for a in paragraph.iterancestors(_SCOPE_ANCESTOR[scope])), None)
            if target is None:
                raise OdtTemplateError(
                    f"La balise « {{%{scope} {body} %}} » doit être dans "
                    f"{'une ligne de tableau' if scope == 'tr' else 'un élément de liste'}"
                )
            if _text_of(target) != _text_of(paragraph):
                raise OdtTemplateError(
                    f"La balise « {{%{scope} {body} %}} » doit être seule dans sa "
                    f"{'ligne de tableau' if scope == 'tr' else 'puce'} (les autres cellules doivent être vides)"
                )
        _insert_text_at(target, "{% " + body + " %}")


# --- Compilation et rendu ----------------------------------------------------------------


def _unescape_tags(xml: str) -> str:
    """lxml échappe ``< > & "`` dans le texte : à l'intérieur d'une balise Jinja, ils doivent redevenir
    des caractères (``{% if a > 3 %}``)."""
    return _TAG.sub(lambda m: html.unescape(m.group(0)), xml)


def compile_part(xml: bytes) -> str:
    """XML d'une partie de l'ODT -> source Jinja (balises fusionnées, blocs structurels posés)."""
    root = _parse(xml)
    for paragraph in root.iter(*_PARAGRAPHS):
        _merge_fragmented_tags(paragraph)
    _apply_scoped_blocks(root)
    source = etree.tostring(root, encoding="unicode")
    return _unescape_tags(source)


def _odt_escape(value: Any) -> str:
    """Valeur -> texte ODT : échappée, avec retours à la ligne, tabulations et espaces multiples
    rendus par les éléments ODT qui leur correspondent."""
    if value is None:
        return ""
    text = _XML_FORBIDDEN.sub("", str(value))
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\r\n|\r|\n", "<text:line-break/>", text)
    text = text.replace("\t", "<text:tab/>")
    return re.sub(r" {2,}", lambda m: " " + f'<text:s text:c="{len(m.group(0)) - 1}"/>', text)


def _environment() -> SandboxedEnvironment:
    # Bac à sable : un modèle ne peut pas appeler d'attributs ou de fonctions dangereux.
    # StrictUndefined : un champ sans valeur est une erreur, jamais un trou silencieux.
    return SandboxedEnvironment(undefined=StrictUndefined, finalize=_odt_escape, autoescape=False)


def _sources(odt: zipfile.ZipFile) -> dict[str, str]:
    return {name: compile_part(odt.read(name)) for name in RENDERED_PARTS if name in odt.namelist()}


def extract_fields(odt: bytes) -> list[str]:
    """Champs utilisés par le modèle (noms de premier niveau, variables de boucle exclues), triés.
    Sert à valider qu'un modèle et sa définition de champs se correspondent."""
    environment = _environment()
    names: set[str] = set()
    for name, source in _sources(_read(odt)).items():
        try:
            names |= meta.find_undeclared_variables(environment.parse(source))
        except TemplateSyntaxError as error:
            raise OdtTemplateError(f"Balise invalide dans {name} (ligne {error.lineno}) : {error.message}") from error
    return sorted(names)


def render(odt: bytes, values: dict[str, Any]) -> bytes:
    """Remplit le modèle avec les valeurs. Lève MissingValueError si un champ n'a pas de valeur et
    OdtTemplateError si le modèle est invalide ou si le résultat n'est pas du XML valide."""
    archive = _read(odt)
    environment = _environment()
    rendered: dict[str, bytes] = {}
    for name, source in _sources(archive).items():
        try:
            output = environment.from_string(source).render(**values)
        except UndefinedError as error:
            raise MissingValueError(f"Aucune valeur pour le champ du modèle : {error.message}") from error
        except SecurityError as error:
            raise OdtTemplateError(f"Expression interdite dans {name} : {error}") from error
        except TemplateSyntaxError as error:
            raise OdtTemplateError(f"Balise invalide dans {name} (ligne {error.lineno}) : {error.message}") from error
        data = (_XML_DECLARATION + output).encode("utf-8")
        _parse(data)  # le résultat doit rester du XML valide
        rendered[name] = data
    return _write(archive, rendered)


def iter_tags(odt: bytes) -> Iterator[str]:
    """Balises présentes dans le modèle (diagnostic)."""
    for source in _sources(_read(odt)).values():
        yield from (m.group(0) for m in _TAG.finditer(source))
