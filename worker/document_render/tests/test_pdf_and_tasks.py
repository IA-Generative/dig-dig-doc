"""Tests de la conversion PDF et des tâches (issue #146)."""

import io
import shutil
import stat
import zipfile
from pathlib import Path

import pytest

from app import pdf, tasks
from app.pdf import PdfConversionError, odt_to_pdf
from tests.conftest import make_odt

needs_libreoffice = pytest.mark.skipif(shutil.which("soffice") is None, reason="LibreOffice (soffice) absent")
FIXTURE = Path(__file__).parent / "fixtures" / "modele-libreoffice.odt"


def test_a_missing_libreoffice_binary_is_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf.settings, "SOFFICE_BINARY", "/nonexistent/soffice")
    with pytest.raises(PdfConversionError, match="introuvable"):
        odt_to_pdf(make_odt("<text:p>x</text:p>"))


def _fake_soffice(tmp_path: Path, script: str) -> str:
    path = tmp_path / "soffice"
    path.write_text("#!/bin/sh\n" + script)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


def test_a_conversion_that_hangs_is_killed_after_the_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pdf.settings, "SOFFICE_BINARY", _fake_soffice(tmp_path, "sleep 30\n"))
    with pytest.raises(PdfConversionError, match="interrompue"):
        odt_to_pdf(make_odt("<text:p>x</text:p>"), timeout=1)


def test_a_failing_conversion_reports_libreoffice_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pdf.settings, "SOFFICE_BINARY", _fake_soffice(tmp_path, "echo 'boom' >&2\nexit 3\n"))
    with pytest.raises(PdfConversionError, match="code 3.*boom"):
        odt_to_pdf(make_odt("<text:p>x</text:p>"))


def test_a_conversion_without_output_file_is_an_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pdf.settings, "SOFFICE_BINARY", _fake_soffice(tmp_path, "exit 0\n"))
    with pytest.raises(PdfConversionError, match="pas produit de PDF"):
        odt_to_pdf(make_odt("<text:p>x</text:p>"))


@needs_libreoffice
@pytest.mark.libreoffice
def test_libreoffice_converts_a_real_template_to_pdf() -> None:
    from app import odt_template

    filled = odt_template.render(
        FIXTURE.read_bytes(),
        {"nom": "Dupont", "adresse": "12 rue des Lilas", "prenom": "Jean", "entites": [{"nom": "a", "valeur": "b"}]},
    )
    result = odt_to_pdf(filled)
    assert result.startswith(b"%PDF-") and len(result) > 1000


@needs_libreoffice
@pytest.mark.libreoffice
def test_concurrent_conversions_do_not_block_each_other() -> None:
    from concurrent.futures import ThreadPoolExecutor

    odt = make_odt("<text:p>Bonjour</text:p>")
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda _: odt_to_pdf(odt, timeout=60), range(3)))
    assert all(r.startswith(b"%PDF-") for r in results)  # un profil par conversion : pas de blocage


def test_garbage_input_is_refused_before_libreoffice_sees_it() -> None:
    # LibreOffice produirait un PDF de n'importe quel texte : l'entrée est vérifiée avant.
    with pytest.raises(PdfConversionError, match="ODT"):
        odt_to_pdf(b"pas un document")


# --- Tâches (S3 simulé) ---


class _FakeStorage:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = dict(objects)

    def get_object(self, key: str) -> bytes:
        return self.objects[key]

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data


def test_extract_template_fields_task(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        tasks, "storage", _FakeStorage({"modeles/m.odt": make_odt("<text:p>{{ nom }} {{ adresse }}</text:p>")})
    )
    assert tasks.extract_template_fields.run("modeles/m.odt") == ["adresse", "nom"]


def test_render_document_task_stores_the_odt_and_the_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeStorage({"modeles/m.odt": make_odt("<text:p>{{ nom }}</text:p>")})
    monkeypatch.setattr(tasks, "storage", fake)
    monkeypatch.setattr(tasks, "odt_to_pdf", lambda odt: b"%PDF-fake")

    result = tasks.render_document.run("modeles/m.odt", {"nom": "Dupont"}, "documents/d1")

    assert result == {"odt_key": "documents/d1.odt", "pdf_key": "documents/d1.pdf"}
    assert b"Dupont" in zipfile.ZipFile(io.BytesIO(fake.objects["documents/d1.odt"])).read("content.xml")
    assert fake.objects["documents/d1.pdf"] == b"%PDF-fake"


def test_render_document_without_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeStorage({"m": make_odt("<text:p>{{ nom }}</text:p>")})
    monkeypatch.setattr(tasks, "storage", fake)
    monkeypatch.setattr(tasks, "odt_to_pdf", lambda odt: pytest.fail("pas de PDF demandé"))
    assert tasks.render_document.run("m", {"nom": "x"}, "out", with_pdf=False) == {"odt_key": "out.odt"}


def test_render_document_fails_loudly_on_a_missing_value(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.odt_template import MissingValueError

    fake = _FakeStorage({"m": make_odt("<text:p>{{ nom }} {{ adresse }}</text:p>")})
    monkeypatch.setattr(tasks, "storage", fake)
    with pytest.raises(MissingValueError, match="adresse"):
        tasks.render_document.run("m", {"nom": "x"}, "out")
    assert "out.odt" not in fake.objects  # rien n'est déposé à moitié


def test_render_preview_task_stores_only_a_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeStorage({"m": make_odt("<text:p>{{ nom }}</text:p>")})
    monkeypatch.setattr(tasks, "storage", fake)
    monkeypatch.setattr(tasks, "odt_to_pdf", lambda odt: b"%PDF-preview")
    assert tasks.render_preview.run("m", {"nom": "x"}, "apercus/p1.pdf") == "apercus/p1.pdf"
    assert fake.objects["apercus/p1.pdf"] == b"%PDF-preview" and list(fake.objects) == ["m", "apercus/p1.pdf"]
