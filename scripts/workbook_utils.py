"""Utilità per modificare il workbook con openpyxl senza perdere ciò che openpyxl non gestisce.

`salva(wb, percorso)`:
1. salva il workbook con openpyxl;
2. **riempie la cache dei valori delle formule** (`riempi_cache`): Excel salva ogni formula insieme al suo ultimo
   risultato, openpyxl invece non sa calcolare e lascia il risultato vuoto. Chi legge il file senza ricalcolare
   (l'export con `data_only=True`, il visualizzatore di VS Code, le anteprime) vedrebbe celle vuote. Qui le formule
   del workbook vengono calcolate in Python (solo le funzioni elencate in `FUNZIONI`) e il risultato viene scritto
   accanto a ogni formula, come farebbe Excel. Excel le ricalcola comunque all'apertura (`fullCalcOnLoad`);
3. reinserisce le parti `xl/webextensions/*` (il collegamento al componente aggiuntivo Claude per Excel), che
   openpyxl scarta, copiandole dal file originale.
"""
from __future__ import annotations

import math
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

TIPI_WEBEXT = {
    "/xl/webextensions/taskpanes.xml": "application/vnd.ms-office.webextensiontaskpanes+xml",
    "/xl/webextensions/webextension1.xml": "application/vnd.ms-office.webextension+xml",
}
REL_TASKPANES = "http://schemas.microsoft.com/office/2011/relationships/webextensiontaskpanes"


def salva(wb, percorso: str | Path, originale: str | Path | None = None) -> list[str]:
    """Salva `wb` in `percorso`, riempie la cache delle formule e reinserisce le parti xl/webextensions di
    `originale` (default: `percorso`). Restituisce le celle con formula che non è stato possibile calcolare."""
    percorso = Path(percorso)
    originale = Path(originale) if originale else percorso
    fd, tmp = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    try:
        wb.save(tmp)
        non_calcolate = riempi_cache(Path(tmp))
        if originale.exists():
            reinserisci_webextensions(originale, Path(tmp))
        shutil.move(tmp, percorso)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return non_calcolate


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
