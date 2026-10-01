"""Tests du remplissage de modèles ODT (issue #146)."""

import html
import io
import re
import zipfile
from pathlib import Path

import pytest
from lxml import etree

from app import odt_template
from app.odt_template import MissingValueError, OdtTemplateError
from tests.conftest import make_odt, read_part

FIXTURE = Path(__file__).parent / "fixtures" / "modele-libreoffice.odt"


def _text(odt: bytes, part: str = "content.xml") -> str:
    """Texte brut d'une partie (les balises XML retirées)."""
    return html.unescape(re.sub(r"<[^>]+>", "", read_part(odt, part)))


def _p(text: str) -> str:
    return f"<text:p>{text}</text:p>"


# --- Champs simples ---


def test_simple_fields_are_filled() -> None:
    odt = make_odt(_p("Nom : {{ nom }}, adresse : {{ adresse }}"))
    out = odt_template.render(odt, {"nom": "Dupont", "adresse": "12 rue des Lilas"})
    assert "Nom : Dupont, adresse : 12 rue des Lilas" in _text(out)
    assert "{{" not in read_part(out)


def test_accents_and_typography_are_kept() -> None:
    out = odt_template.render(make_odt(_p("{{ v }}")), {"v": "Éloïse d'Hérouville — « ça » ’ 5 €"})
    assert "Éloïse d'Hérouville — « ça » ’ 5 €" in _text(out)


def test_xml_special_characters_are_escaped_not_interpreted() -> None:
    value = 'Dupont & fils <b>gras</b> "citation" > 3'
    out = odt_template.render(make_odt(_p("{{ v }}")), {"v": value})
    etree.fromstring(read_part(out).encode())  # toujours du XML valide
    assert "Dupont &amp; fils" in read_part(out)
    assert "<b>" not in read_part(out)  # la balise de la valeur n'est pas devenue du XML
    assert "&lt;b&gt;gras&lt;/b&gt;" in read_part(out)


def test_newlines_tabs_and_repeated_spaces_become_odt_elements() -> None:
    out = odt_template.render(make_odt(_p("{{ v }}")), {"v": "ligne 1\nligne 2\r\nligne 3\tcol  deux   trois"})
    xml = read_part(out)
    assert xml.count("<text:line-break/>") == 2
    assert "<text:tab/>" in xml
    assert 'text:c="1"' in xml and 'text:c="2"' in xml  # espaces multiples conservés


def test_none_is_empty_and_numbers_are_text() -> None:
    out = odt_template.render(make_odt(_p("[{{ a }}] [{{ b }}] [{{ c }}]")), {"a": None, "b": 42, "c": 3.5})
    assert "[] [42] [3.5]" in _text(out)


def test_xml_forbidden_control_characters_are_dropped() -> None:
    out = odt_template.render(make_odt(_p("{{ v }}")), {"v": "a\x00b\x0bc\x1fd"})
    etree.fromstring(read_part(out).encode())
    assert "abcd" in _text(out)


def test_a_very_long_value_is_kept_whole() -> None:
    value = "mot " * 20000
    out = odt_template.render(make_odt(_p("{{ v }}")), {"v": value})
    assert len(_text(out)) >= len(value.replace("  ", " "))


# --- Placeholders fragmentés par LibreOffice ---


def test_a_placeholder_split_across_spans_is_filled() -> None:
    body = _p(
        'Nom : {{ <text:span text:style-name="T1">pre</text:span><text:span text:style-name="T2">nom</text:span> }}.'
    )
    out = odt_template.render(make_odt(body), {"prenom": "Jean"})
    assert "Nom : Jean." in _text(out)
    assert "pre" not in _text(out)  # aucun fragment du placeholder ne subsiste


def test_a_tag_split_in_three_spans_and_neighbours_are_kept() -> None:
    body = _p(
        'Avant <text:span text:style-name="T2">italique</text:span> {<text:span text:style-name="T1">{ n</text:span>'
        '<text:span text:style-name="T2">om }</text:span>} après'
    )
    out = odt_template.render(make_odt(body), {"nom": "Dupont"})
    text = _text(out)
    assert "Avant italique Dupont après" in text
    assert 'text:style-name="T2">italique' in read_part(out)  # le span non concerné est intact


def test_two_fragmented_tags_in_one_paragraph() -> None:
    body = _p(
        '{{ a<text:span text:style-name="T1">a</text:span> }} et {{ b<text:span text:style-name="T2">b</text:span> }}'
    )
    out = odt_template.render(make_odt(body), {"aa": "1", "bb": "2"})
    assert "1 et 2" in _text(out)


def test_placeholders_split_in_the_header_of_styles_xml() -> None:
    header = _p('Dossier {{ <text:span text:style-name="T1">ref</text:span>erence }}')
    odt = make_odt(_p("corps"), header=header)
    out = odt_template.render(odt, {"reference": "2026-0042"})
    assert "Dossier 2026-0042" in _text(out, "styles.xml")


def test_extraction_sees_fragmented_and_header_fields() -> None:
    header = _p("Réf {{ reference }}")
    odt = make_odt(_p('{{ <text:span text:style-name="T1">pre</text:span>nom }} {{ nom }}'), header=header)
    assert sorted(odt_template.extract_fields(odt)) == ["nom", "prenom", "reference"]


# --- Blocs : paragraphes, lignes de tableau, puces ---

ROWS = [{"nom": "nom", "valeur": "Dupont"}, {"nom": "adresse", "valeur": "12 rue X"}, {"nom": "tél", "valeur": "06"}]


def _table(*rows: str) -> str:
    return '<table:table table:name="T"><table:table-column/>' + "".join(rows) + "</table:table>"


def _row(*cells: str) -> str:
    return (
        "<table:table-row>"
        + "".join(f"<table:table-cell>{_p(c)}</table:table-cell>" for c in cells)
        + "</table:table-row>"
    )


def test_table_rows_are_repeated_and_control_rows_removed() -> None:
    body = _table(
        _row("Entité", "Valeur"),
        _row("{%tr for e in entites %}", ""),
        _row("{{ e.nom }}", "{{ e.valeur }}"),
        _row("{%tr endfor %}", ""),
    )
    out = odt_template.render(make_odt(body), {"entites": ROWS})
    xml = read_part(out)
    assert xml.count("<table:table-row>") == 1 + 3  # l'en-tête et trois lignes
    assert "{%" not in xml
    for row in ROWS:
        assert row["nom"] in _text(out) and row["valeur"] in _text(out)


def test_an_empty_list_leaves_only_the_header_row() -> None:
    body = _table(
        _row("Entité", "Valeur"),
        _row("{%tr for e in entites %}", ""),
        _row("{{ e.nom }}", "{{ e.valeur }}"),
        _row("{%tr endfor %}", ""),
    )
    out = odt_template.render(make_odt(body), {"entites": []})
    assert read_part(out).count("<table:table-row>") == 1


def test_paragraph_blocks_are_repeated() -> None:
    body = (
        _p("Début")
        + _p("{%p for e in entites %}")
        + _p("- {{ e.nom }} : {{ e.valeur }}")
        + _p("{%p endfor %}")
        + _p("Fin")
    )
    out = odt_template.render(make_odt(body), {"entites": ROWS})
    assert read_part(out).count("<text:p>") == 2 + 3
    assert "- nom : Dupont" in _text(out) and "- tél : 06" in _text(out)


def test_list_items_are_repeated() -> None:
    body = (
        "<text:list>"
        "<text:list-item>" + _p("{%li for e in entites %}") + "</text:list-item>"
        "<text:list-item>" + _p("{{ e.nom }}") + "</text:list-item>"
        "<text:list-item>" + _p("{%li endfor %}") + "</text:list-item>"
        "</text:list>"
    )
    out = odt_template.render(make_odt(body), {"entites": ROWS})
    assert read_part(out).count("<text:list-item>") == 3


def test_inline_loop_and_conditions_in_one_paragraph() -> None:
    body = _p(
        "{% for e in entites %}{{ e.nom }}{% if not loop.last %}, {% endif %}{% endfor %} "
        "({% if n > 2 %}beaucoup{% else %}peu{% endif %})"
    )
    out = odt_template.render(make_odt(body), {"entites": ROWS, "n": 3})
    assert "nom, adresse, tél (beaucoup)" in _text(out)


def test_a_loop_variable_is_not_reported_as_a_field() -> None:
    body = _table(_row("{%tr for e in entites %}", ""), _row("{{ e.nom }}", "{{ titre }}"), _row("{%tr endfor %}", ""))
    assert odt_template.extract_fields(make_odt(body)) == ["entites", "titre"]


# --- Champs manquants et modèles invalides ---


def test_a_missing_value_is_an_error_naming_the_field() -> None:
    with pytest.raises(MissingValueError, match="adresse"):
        odt_template.render(make_odt(_p("{{ nom }} {{ adresse }}")), {"nom": "Dupont"})


def test_a_missing_attribute_of_a_list_item_is_an_error() -> None:
    body = _p("{% for e in entites %}{{ e.absent }}{% endfor %}")
    with pytest.raises(MissingValueError):
        odt_template.render(make_odt(body), {"entites": ROWS})


def test_a_malformed_tag_is_a_template_error() -> None:
    with pytest.raises(OdtTemplateError, match="Balise invalide"):
        odt_template.extract_fields(make_odt(_p("{% for e in %}")))


def test_an_unclosed_block_is_a_template_error() -> None:
    with pytest.raises(OdtTemplateError):
        odt_template.render(make_odt(_p("{%p for e in entites %}") + _p("{{ e.nom }}")), {"entites": ROWS})


def test_a_row_control_tag_must_be_alone_in_its_row() -> None:
    body = _table(_row("{%tr for e in entites %}", "autre texte"), _row("{{ e.nom }}", ""), _row("{%tr endfor %}", ""))
    with pytest.raises(OdtTemplateError, match="seule"):
        odt_template.render(make_odt(body), {"entites": ROWS})


def test_a_row_control_tag_outside_a_table_is_refused() -> None:
    with pytest.raises(OdtTemplateError, match="ligne de tableau"):
        odt_template.render(make_odt(_p("{%tr for e in entites %}")), {"entites": ROWS})


def test_the_sandbox_refuses_dangerous_expressions() -> None:
    with pytest.raises(OdtTemplateError, match="interdite"):
        odt_template.render(make_odt(_p("{{ ''.__class__.__mro__ }}")), {})


def test_a_file_that_is_not_an_odt_is_refused() -> None:
    with pytest.raises(OdtTemplateError, match="archive"):
        odt_template.extract_fields(b"ceci n'est pas un zip")


# --- L'archive est conservée ---


def test_other_files_are_copied_untouched_and_mimetype_stays_first_and_stored() -> None:
    odt = make_odt(_p("{{ nom }}"), extra={"Pictures/logo.png": b"\x89PNG-fake-bytes", "meta.xml": b"<meta/>"})
    out = odt_template.render(odt, {"nom": "Dupont"})
    before, after = zipfile.ZipFile(io.BytesIO(odt)), zipfile.ZipFile(io.BytesIO(out))
    assert after.namelist() == before.namelist()
    assert after.infolist()[0].filename == "mimetype" and after.infolist()[0].compress_type == zipfile.ZIP_STORED
    for name in ("Pictures/logo.png", "meta.xml", "META-INF/manifest.xml", "mimetype"):
        assert after.read(name) == before.read(name)


def test_rendering_is_deterministic() -> None:
    odt = make_odt(_p("{{ nom }}"))
    assert odt_template.render(odt, {"nom": "Dupont"}) == odt_template.render(odt, {"nom": "Dupont"})


def test_the_result_is_valid_xml_in_every_part() -> None:
    out = odt_template.render(make_odt(_p("{{ v }}"), header=_p("{{ v }}")), {"v": "a & b < c"})
    for part in ("content.xml", "styles.xml"):
        etree.fromstring(read_part(out, part).encode())


# --- Modèle réel produit par LibreOffice ---


def test_a_libreoffice_template_with_a_fragmented_placeholder_is_filled() -> None:
    template = FIXTURE.read_bytes()
    assert odt_template.extract_fields(template) == ["adresse", "entites", "nom", "prenom"]
    out = odt_template.render(
        template,
        {"nom": "Dupont & fils", "adresse": "12 rue des Lilas", "prenom": "Jean", "entites": ROWS},
    )
    text = _text(out)
    assert "Dupont & fils" in text
    assert "Fragmenté : Jean" in text
    assert "{{" not in read_part(out) and "{%" not in read_part(out)
    assert zipfile.ZipFile(io.BytesIO(out)).testzip() is None
