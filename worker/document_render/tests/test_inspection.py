"""Tests du contrôle d'un modèle à l'import (issue #148)."""

import shutil
import subprocess
from typing import Any

import pytest

from app import inspection, odt_template, tasks
from tests.conftest import font_styles, make_odt

needs_fontconfig = pytest.mark.skipif(shutil.which("fc-match") is None, reason="fontconfig (fc-match) absent")


def p(text: str) -> str:
    return f"<text:p>{text}</text:p>"


def fake_fc(monkeypatch: pytest.MonkeyPatch, answers: dict[str, str | None]) -> None:
    """Remplace fc-match : renvoie la police la plus proche de chaque famille (None : échec)."""

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
        family = command[1]
        answer = answers.get(family)
        return subprocess.CompletedProcess(command, 0 if answer else 1, stdout=(answer or "") + "\n", stderr="")

    monkeypatch.setattr(inspection.subprocess, "run", run)


# --- Polices utilisées ---


def test_the_fonts_a_template_uses_are_listed_in_order() -> None:
    odt = make_odt(p("x"), content_prefix=font_styles("Marianne", "Arial", "Marianne"))
    assert inspection.used_fonts(odt) == ["Marianne", "Arial"]


def test_declared_but_unused_fonts_and_generic_families_are_ignored() -> None:
    # Police déclarée mais qu'aucun style ne référence : valeur par défaut de LibreOffice, pas un choix de l'auteur.
    prefix = (
        '<office:font-face-decls><style:font-face style:name="Lucida Sans" svg:font-family="\'Lucida Sans\'"/>'
        '<style:font-face style:name="Lib" svg:font-family="\'Liberation Serif\', serif"/></office:font-face-decls>'
        '<office:automatic-styles><style:style style:name="T" style:family="text">'
        '<style:text-properties style:font-name="Lib" fo:font-family="sans-serif"/></style:style>'
        "</office:automatic-styles>"
    )
    assert inspection.used_fonts(make_odt(p("x"), content_prefix=prefix)) == ["Liberation Serif"]


def test_a_direct_font_family_is_listed_too() -> None:
    prefix = (
        '<office:automatic-styles><style:style style:name="T" style:family="text">'
        '<style:text-properties fo:font-family="Gill Sans"/></style:style></office:automatic-styles>'
    )
    assert inspection.used_fonts(make_odt(p("x"), content_prefix=prefix)) == ["Gill Sans"]


def test_a_template_without_font_styles_has_no_fonts() -> None:
    assert inspection.used_fonts(make_odt(p("x"))) == [] and inspection.used_fonts(b"pas un zip") == []


# --- Disponibilité d'une police ---


def test_an_installed_font_is_reported_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_fc(monkeypatch, {"Liberation Sans": "Liberation Sans"})
    assert inspection.check_font("Liberation Sans").status == "installed"


def test_a_metric_compatible_replacement_is_reported_as_such(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_fc(monkeypatch, {"Arial": "Liberation Sans", "Calibri": "Carlito", "Cambria": "Caladea"})
    arial = inspection.check_font("Arial")
    assert (arial.status, arial.replaced_by) == ("compatible", "Liberation Sans")
    assert (
        inspection.check_font("Calibri").status == "compatible"
        and inspection.check_font("Cambria").status == "compatible"
    )


def test_a_missing_font_is_reported_substituted(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_fc(monkeypatch, {"Marianne": "DejaVu Sans", "Arial": "DejaVu Sans"})
    marianne = inspection.check_font("Marianne")
    assert (marianne.status, marianne.replaced_by) == ("substituted", "DejaVu Sans")
    # « Arial » remplacée par autre chose que son équivalent métrique : la mise en page change.
    assert inspection.check_font("Arial").status == "substituted"


def test_without_fontconfig_a_font_is_unknown_not_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(*args: Any, **kwargs: Any) -> None:
        raise FileNotFoundError("fc-match")

    monkeypatch.setattr(inspection.subprocess, "run", missing)
    assert inspection.check_font("Marianne").status == "unknown"
    fake_fc(monkeypatch, {"Marianne": None})
    assert inspection.check_font("Marianne").status == "unknown"


@needs_fontconfig
def test_with_the_real_fontconfig_arial_is_compatible_and_an_absent_font_is_substituted() -> None:
    # Dans l'image : Liberation remplace Arial (mêmes métriques) ; une police inventée est remplacée par une autre.
    assert inspection.check_font("Arial").status in ("compatible", "installed")
    assert inspection.check_font("Police-Inventée-Pour-Le-Test-148").status == "substituted"


# --- Champs natifs, images ---


def test_native_libreoffice_fields_are_counted_by_kind() -> None:
    first = '<text:user-field-get text:name="nom">x</text:user-field-get>'
    second = '<text:variable-get text:name="v">y</text:variable-get>'
    third = '<text:text-input>z</text:text-input><text:user-field-get text:name="autre">w</text:user-field-get>'
    body = p(f"{first} {second}") + p(third)
    assert inspection.native_fields(make_odt(body)) == {"champ utilisateur": 2, "variable": 1, "champ de saisie": 1}


def test_fields_libreoffice_computes_itself_are_not_flagged() -> None:
    assert (
        inspection.native_fields(
            make_odt(p("Page <text:page-number>1</text:page-number> le <text:date>2026</text:date>"))
        )
        == {}
    )


def test_images_are_counted() -> None:
    body = p('<draw:frame><draw:image xlink:href="Pictures/logo.png"/></draw:frame>')
    assert inspection.image_count(make_odt(body)) == 1 and inspection.image_count(make_odt(p("x"))) == 0


# --- Rapport ---


def test_the_report_warns_about_what_will_surprise_without_blocking(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_fc(monkeypatch, {"Marianne": "DejaVu Sans", "Arial": "Liberation Sans"})
    body = (
        p("{{ nom }}")
        + p('<text:user-field-get text:name="n">x</text:user-field-get>')
        + p('<draw:frame><draw:image xlink:href="Pictures/logo.png"/></draw:frame>')
    )
    report = inspection.inspect(make_odt(body, content_prefix=font_styles("Marianne", "Arial")))

    assert {f["name"]: f["status"] for f in report["fonts"]} == {"Marianne": "substituted", "Arial": "compatible"}
    by_code = {w["code"]: w for w in report["warnings"]}
    assert set(by_code) == {"font_substituted", "native_field", "images"}
    assert (
        "« Marianne »" in by_code["font_substituted"]["message"]
        and "« DejaVu Sans »" in by_code["font_substituted"]["message"]
    )
    assert by_code["font_substituted"]["level"] == "warning" and by_code["images"]["level"] == "info"
    assert "1 champ utilisateur(s) natif(s)" in by_code["native_field"]["message"]


def test_a_clean_template_has_no_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_fc(monkeypatch, {"Arial": "Liberation Sans"})
    assert inspection.inspect(make_odt(p("{{ nom }}"), content_prefix=font_styles("Arial")))["warnings"] == []


def test_unverifiable_fonts_are_an_info_not_a_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_fc(monkeypatch, {"Marianne": None})
    report = inspection.inspect(make_odt(p("x"), content_prefix=font_styles("Marianne")))
    assert [(w["code"], w["level"]) for w in report["warnings"]] == [("fonts_unchecked", "info")]


# --- Tâche ---


class _Storage:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def get_object(self, key: str) -> bytes:
        return self.data


def test_the_task_returns_fields_fonts_and_warnings(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_fc(monkeypatch, {"Marianne": "DejaVu Sans"})
    odt = make_odt(p("{{ nom }} {{ adresse }}"), content_prefix=font_styles("Marianne"))
    monkeypatch.setattr(tasks, "storage", _Storage(odt))

    result = tasks.inspect_template.run("modeles/m.odt")

    assert result["fields"] == ["adresse", "nom"]
    assert result["fonts"] == [{"name": "Marianne", "status": "substituted", "replaced_by": "DejaVu Sans"}]
    assert [w["code"] for w in result["warnings"]] == ["font_substituted"]


def test_an_invalid_template_is_still_an_error_not_a_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tasks, "storage", _Storage(make_odt(p("{% for e in %}"))))
    with pytest.raises(odt_template.OdtTemplateError):
        tasks.inspect_template.run("m.odt")


# --- Cadres, en-têtes : les placeholders y sont remplis comme ailleurs ---


def test_placeholders_in_a_frame_a_text_box_and_a_header_are_found_and_filled() -> None:
    body = p("{{ corps }}") + (
        "<draw:frame><draw:text-box><text:p>Réf. {{ reference }}</text:p></draw:text-box></draw:frame>"
    )
    odt = make_odt(body, header=p("Dossier {{ dossier }}"))

    assert odt_template.extract_fields(odt) == ["corps", "dossier", "reference"]
    out = odt_template.render(odt, {"corps": "C", "reference": "R-1", "dossier": "D-9"})
    from tests.conftest import read_part

    assert "Réf. R-1" in read_part(out) and "Dossier D-9" in read_part(out, "styles.xml")
