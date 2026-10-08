"""Utilità per modificare il workbook con openpyxl senza perdere parti che openpyxl non gestisce.

openpyxl, al salvataggio, scarta le parti `xl/webextensions/*` (il collegamento al componente aggiuntivo
Claude per Excel). `salva(wb, percorso)` salva il workbook e poi le reinserisce copiandole dal file originale.

Ricorda: salvando fuori da Excel la cache dei valori delle formule si svuota. L'export la ricalcola,
ma il file va poi aperto e salvato in Excel (CLAUDE.md §3 e §11).
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

TIPI_WEBEXT = {
    "/xl/webextensions/taskpanes.xml": "application/vnd.ms-office.webextensiontaskpanes+xml",
    "/xl/webextensions/webextension1.xml": "application/vnd.ms-office.webextension+xml",
}
REL_TASKPANES = "http://schemas.microsoft.com/office/2011/relationships/webextensiontaskpanes"


def salva(wb, percorso: str | Path, originale: str | Path | None = None) -> None:
    """Salva `wb` in `percorso` reinserendo le parti xl/webextensions di `originale` (default: `percorso`)."""
    percorso = Path(percorso)
    originale = Path(originale) if originale else percorso
    fd, tmp = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    try:
        wb.save(tmp)
        if originale.exists():
            reinserisci_webextensions(originale, Path(tmp))
        shutil.move(tmp, percorso)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def reinserisci_webextensions(originale: Path, nuovo: Path) -> bool:
    """Copia in `nuovo` le parti xl/webextensions di `originale` con relazioni e content type. True se ne ha copiate."""
    with zipfile.ZipFile(originale) as zo:
        parti = {n: zo.read(n) for n in zo.namelist() if n.startswith("xl/webextensions/")}
    if not parti:
        return False
    with zipfile.ZipFile(nuovo) as zn:
        contenuti = {n: zn.read(n) for n in zn.namelist()}
    contenuti.update(parti)

    rels = contenuti["_rels/.rels"].decode()
    if REL_TASKPANES not in rels:
        nuovo_id = max((int(x) for x in re.findall(r'Id="rId(\d+)"', rels)), default=0) + 1
        rels = rels.replace("</Relationships>", f'<Relationship Id="rId{nuovo_id}" Type="{REL_TASKPANES}" '
                                                 'Target="xl/webextensions/taskpanes.xml"/></Relationships>')
        contenuti["_rels/.rels"] = rels.encode()

    ct = contenuti["[Content_Types].xml"].decode()
    for parte, tipo in TIPI_WEBEXT.items():
        if parte.lstrip("/") in parti and f'PartName="{parte}"' not in ct:
            ct = ct.replace("</Types>", f'<Override PartName="{parte}" ContentType="{tipo}"/></Types>')
    contenuti["[Content_Types].xml"] = ct.encode()

    ordine = ["[Content_Types].xml"] + [n for n in contenuti if n != "[Content_Types].xml"]
    with zipfile.ZipFile(nuovo, "w", zipfile.ZIP_DEFLATED) as z:
        for n in ordine:
            z.writestr(n, contenuti[n])
    return True
