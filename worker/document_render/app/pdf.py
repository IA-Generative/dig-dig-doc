"""Conversion d'un document ODT en PDF avec LibreOffice (issue #146, parent #107).

LibreOffice sert ici **uniquement** à produire le PDF (aperçu et export) : c'est le même moteur
qui a servi à concevoir le modèle, donc la mise en page est celle que voit son auteur.
Précautions :

- **un profil LibreOffice temporaire par conversion** : deux conversions simultanées avec le
  même profil se bloquent ou échouent ; avec un profil chacune, elles peuvent s'exécuter en
  parallèle ;
- **macros désactivées** (niveau de sécurité maximal) et pas de mise à jour des liens externes ;
- **délai maximal** : au-delà, le groupe de processus (soffice et soffice.bin) est tué ;
- les polices utilisées sont celles **installées dans l'image** : une police absente est
  remplacée, et le rendu diffère alors de celui de l'auteur.
"""

import io
import os
import signal
import subprocess
import tempfile
import zipfile
from pathlib import Path

from app.config import settings

# Niveau de sécurité des macros « très élevé » : aucune macro ne s'exécute (le modèle est un
# fichier déposé par un administrateur, mais rien ne justifie d'exécuter du code).
_REGISTRY = """<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
 <item oor:path="/org.openoffice.Office.Common/Security/Scripting">
  <prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop>
  <prop oor:name="DisableMacrosExecution" oor:op="fuse"><value>true</value></prop>
 </item>
</oor:items>
"""


class PdfConversionError(RuntimeError):
    """LibreOffice n'a pas produit de PDF (document illisible, délai dépassé, binaire absent…)."""


def _check_is_odt(odt: bytes) -> None:
    """LibreOffice convertit n'importe quel texte en PDF au lieu d'échouer : on vérifie donc l'entrée."""
    try:
        mimetype = zipfile.ZipFile(io.BytesIO(odt)).read("mimetype")
    except (zipfile.BadZipFile, KeyError) as error:
        raise PdfConversionError("Le contenu à convertir n'est pas un document ODT") from error
    if mimetype.strip() != b"application/vnd.oasis.opendocument.text":
        raise PdfConversionError("Le contenu à convertir n'est pas un document texte ODT")


def odt_to_pdf(odt: bytes, *, timeout: int | None = None) -> bytes:
    _check_is_odt(odt)
    timeout = timeout or settings.SOFFICE_TIMEOUT_SECONDS
    with tempfile.TemporaryDirectory(prefix="render-") as tmp:
        work = Path(tmp)
        source = work / "document.odt"
        source.write_bytes(odt)
        profile = work / "profile"
        (profile / "user").mkdir(parents=True)
        (profile / "user" / "registrymodifications.xcu").write_text(_REGISTRY, encoding="utf-8")
        command = [
            settings.SOFFICE_BINARY,
            "--headless",
            "--norestore",
            "--nolockcheck",
            "--nodefault",
            "--nofirststartwizard",
            f"-env:UserInstallation={profile.as_uri()}",
            "--convert-to",
            "pdf:writer_pdf_Export",
            "--outdir",
            str(work),
            str(source),
        ]
        try:
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True, cwd=work
            )
        except FileNotFoundError as error:
            raise PdfConversionError(f"LibreOffice introuvable ({settings.SOFFICE_BINARY})") from error
        try:
            _, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            # soffice lance soffice.bin : on tue tout le groupe de processus.
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise PdfConversionError(f"Conversion PDF interrompue après {timeout} s") from error
        pdf = work / "document.pdf"
        if process.returncode != 0 or not pdf.exists():
            detail = stderr.decode("utf-8", errors="replace").strip()[-500:]
            raise PdfConversionError(f"LibreOffice n'a pas produit de PDF (code {process.returncode}) : {detail}")
        return pdf.read_bytes()
