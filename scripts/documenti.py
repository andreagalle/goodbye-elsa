#!/usr/bin/env python3
"""Documenti ufficiali dei fondi: download, testo estratto e indice per il sito.

Il registro data/documenti.csv (scritto a mano, una riga per documento) dice quali documenti cita la pagina
informativa ufficiale di ogni fondo e da dove si scaricano. Lo script:
  scarica  scarica in docs/documenti/<fondo-id>/<file> i PDF che mancano e ne estrae il testo in <file>.txt
           (intestazione con fonte, data, SHA-256 e numero di pagine, poi "=== pagina N ===" per ogni pagina),
           così si possono consultare e citare con il numero di pagina;
  riprova  riprova i documenti del registro rimasti senza file (siti che bloccano i download o limitano le
           richieste) e, se ci riesce, aggiorna il registro: da lanciare anche da un'altra rete o con --browser;
  smista   smista i PDF messi a mano in documenti-da-smistare/ (es. scaricati dal browser per i siti che bloccano gli
           script): riconosce fondo e tipo dal contenuto, li abbina ai documenti mancanti del registro e, con
           --applica, li sposta nella cartella del fondo, ne estrae il testo e aggiorna il registro;
  indice   rigenera data/documenti.json (copiato in docs/data/ per il sito) e docs/documenti/README.md.
           Non usa la rete né pypdf: la CI lo esegue dopo l'export.

Uso:
  python scripts/documenti.py scarica [--fondo ID ...] [--aggiorna] [--browser]
  python scripts/documenti.py riprova [--fondo ID ...] [--browser] [--pausa SECONDI]
  python scripts/documenti.py smista [--applica]
  python scripts/documenti.py indice [--check] [--no-docs]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRO = ROOT / "data" / "documenti.csv"
FONDI = ROOT / "data" / "fondi.json"
CARTELLA = ROOT / "docs" / "documenti"
INDICE = ROOT / "data" / "documenti.json"
INDICE_SITO = ROOT / "docs" / "data" / "documenti.json"
README = CARTELLA / "README.md"
CASSETTA = ROOT / "documenti-da-smistare"  # PDF aggiunti a mano, da smistare con il comando smista

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
CAMPI = ["fondo_id", "tipo", "titolo", "file", "url", "pagina", "referenziato", "note"]

# Tipi di documento, nell'ordine in cui compaiono nel sito (nome, a cosa serve)
TIPI = {
    "nota-informativa": ("Nota informativa", "Il documento principale del fondo; se il gestore la pubblica intera, contiene anche le schede qui sotto."),
    "scheda-presentazione": ("Nota informativa – Scheda Presentazione", "Parte I: caratteristiche del fondo, comparti e dove trovare le informazioni."),
    "scheda-costi": ("Nota informativa – Scheda I costi", "Parte I: costi in fase di accumulo e Indicatore sintetico dei costi (ISC)."),
    "scheda-destinatari": ("Nota informativa – Scheda I destinatari e i contributi", "Parte I: chi può aderire e quanto si versa (adesioni collettive)."),
    "opzioni-investimento": ("Nota informativa – Scheda Le opzioni di investimento", "Parte II: politica di investimento, rischi e rendimenti passati dei comparti."),
    "soggetti-coinvolti": ("Nota informativa – Scheda Le informazioni sui soggetti coinvolti", "Parte II: gestore, depositario, compagnie per le rendite, revisore."),
    "informativa-sostenibilita": ("Nota informativa – Appendice Informativa sulla sostenibilità", "Come i comparti considerano i fattori ambientali, sociali e di governance (ESG)."),
    "supplemento": ("Supplemento alla Nota informativa", "Le nuove prestazioni introdotte dalla L. 199/2025: rendita a durata definita, prelievi, erogazione frazionata."),
    "regolamento": ("Regolamento", "Le regole del fondo: adesione, contribuzione, prestazioni, trasferimenti e costi."),
    "documento-rendite": ("Documento sulle rendite", "Tipi di rendita, coefficienti di trasformazione, costi e rivalutazione nella fase di erogazione."),
    "documento-anticipazioni": ("Documento sulle anticipazioni", "Quando e quanto si può anticipare, con quali documenti."),
    "documento-regime-fiscale": ("Documento sul regime fiscale", "Deducibilità dei contributi e tassazione di rendimenti e prestazioni."),
    "documento-politica-investimento": ("Documento sulla politica di investimento", "Obiettivi, strategie e controlli della gestione finanziaria."),
    "documento-sistema-governo": ("Documento sul sistema di governo", "Organizzazione, controlli interni e gestione dei rischi."),
    "rendiconto": ("Rendiconto", "Il bilancio annuale del fondo e dei comparti (ultimo pubblicato)."),
    "modulo-adesione": ("Modulo di adesione", "Il modulo per aderire, con le scelte su comparto e contributi."),
    "metodologia-proiezioni": ("Metodologia delle proiezioni", "Come il fondo stima la pensione nel Progetto esemplificativo."),
    "altro": ("Altri documenti", "Altri documenti informativi del fondo citati nella sua pagina."),
}
# Riga del registro che non è un documento ma una nota sul fondo (es. "sito non raggiungibile"): il testo sta in titolo
NOTA_FONDO = "nota-fondo"
INTESTAZIONE_TESTO = "# Testo estratto automaticamente dal PDF con pypdf: tabelle e impaginazione possono risultare alterate; fa fede il PDF."


def leggi_registro(percorso: Path = REGISTRO) -> list[dict]:
    with open(percorso, newline="", encoding="utf-8") as fh:
        r = csv.DictReader(fh)
        if r.fieldnames != CAMPI:
            raise SystemExit(f"{percorso.name}: intestazioni attese {CAMPI}, trovate {r.fieldnames}")
        return [{k: (v or "").strip() for k, v in riga.items()} for riga in r]


def fondi_per_id() -> dict[str, dict]:
    return {f["id"]: f for f in json.loads(FONDI.read_text(encoding="utf-8"))}


def valida(righe: list[dict], fondi: dict[str, dict]) -> list[str]:
    errori, visti = [], set()
    for n, r in enumerate(righe, start=2):
        dove = f"{REGISTRO.name}:{n}"
        if r["fondo_id"] not in fondi:
            errori.append(f"{dove}: fondo '{r['fondo_id']}' non presente in fondi.json")
        if r["tipo"] == NOTA_FONDO:
            if r["file"] or not r["titolo"]:
                errori.append(f"{dove}: una nota sul fondo ha solo il testo (colonna titolo), senza file")
            continue
        if r["tipo"] not in TIPI:
            errori.append(f"{dove}: tipo '{r['tipo']}' sconosciuto")
        if r["referenziato"] not in ("Sì", "No"):
            errori.append(f"{dove}: referenziato deve essere Sì o No")
        if not r["titolo"]:
            errori.append(f"{dove}: titolo mancante")
        if r["file"]:
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.pdf", r["file"]):
                errori.append(f"{dove}: nome file '{r['file']}' non valido (minuscole, cifre e trattini, .pdf)")
            chiave = (r["fondo_id"], r["file"])
            if chiave in visti:
                errori.append(f"{dove}: file {r['file']} ripetuto per {r['fondo_id']}")
            visti.add(chiave)
            if not r["url"] and not r["note"]:
                errori.append(f"{dove}: file senza url di origine né nota sulla provenienza")
        elif not r["note"]:
            errori.append(f"{dove}: documento non scaricato senza una nota che spieghi perché")
    return errori


# ---------------------------------------------------------------- download e testo
def _url_sicuro(url: str) -> str:
    """Codifica spazi e caratteri non ASCII lasciando intatti quelli già codificati."""
    return urllib.parse.quote(url, safe=":/?&=%#+@,;~!$'()*")


def _scarica_urllib(url: str) -> bytes:
    req = urllib.request.Request(_url_sicuro(url), headers={"User-Agent": UA, "Accept": "application/pdf,*/*",
                                                            "Accept-Language": "it-IT,it;q=0.9"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        dati = resp.read()
    # alcuni server (es. unipol.it) comprimono con gzip anche senza Accept-Encoding
    return gzip.decompress(dati) if dati[:2] == b"\x1f\x8b" else dati


def _scarica_curl(url: str) -> bytes:
    """Alcuni server rispondono con una pagina HTML a urllib ma con il PDF a curl."""
    return subprocess.run(["curl", "-s", "-L", "--compressed", "--max-time", "120", "-A", UA, _url_sicuro(url)],
                          capture_output=True, timeout=150, check=True).stdout


def _scarica_browser(url: str, pagina: str) -> bytes:
    """Per i siti che rifiutano i client non-browser: visita la pagina (cookie) e poi chiede il PDF."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(user_agent=UA, locale="it-IT")
        try:
            if pagina:
                ctx.new_page().goto(pagina, wait_until="domcontentloaded", timeout=60000)
            r = ctx.request.get(url, timeout=90000)
            if not r.ok:
                raise RuntimeError(f"HTTP {r.status}")
            return r.body()
        finally:
            b.close()


def estrai_testo(pdf: Path, riga: dict, fondo: dict, scaricato_il: str, provenienza: str = "") -> Path:
    import logging
    from pypdf import PdfReader
    logging.getLogger("pypdf").setLevel(logging.ERROR)  # avvisi sui PDF imperfetti: il testo si estrae comunque
    pagine, n_pagine, problema = [], 0, None
    try:
        lettore = PdfReader(pdf)
        if lettore.is_encrypted:  # cifrati senza password (solo per impedire la modifica): serve cryptography
            lettore.decrypt("")
        n_pagine = len(lettore.pages)
        for i, p in enumerate(lettore.pages, start=1):
            try:
                t = p.extract_text() or ""
            except Exception as e:  # pagine danneggiate: si segnala e si prosegue
                t = f"[testo non estraibile: {e}]"
            pagine.append(f"=== pagina {i} ===\n{t.strip()}\n")
    except Exception as e:  # PDF illeggibile: si conserva comunque il PDF, con il motivo nel testo
        problema = f"{type(e).__name__}: {e}"[:200]
    testo = "".join(pagine)
    nome_tipo = TIPI[riga["tipo"]][0]
    righe = [
        f"# Fondo: {fondo['denominazione']} ({fondo['id']})",
        f"# Documento: {nome_tipo} – {riga['titolo']}",
        f"# Fonte: {riga['url'] or '(nessun link diretto: copia fornita a mano)'}",
        f"# Citato in: {riga['pagina'] or fondo['url']}",
        f"# Scaricato il: {scaricato_il}",
        f"# SHA-256 del PDF: {hashlib.sha256(pdf.read_bytes()).hexdigest()}",
        f"# Pagine: {n_pagine}",
        INTESTAZIONE_TESTO,
    ]
    if provenienza:
        righe.insert(5, f"# Provenienza: {provenienza}")
    if problema:
        righe.append(f"# Attenzione: testo non estraibile ({problema}): consultare il PDF.")
    elif len(re.sub(r"=== pagina \d+ ===|\s", "", testo)) < 50 * n_pagine:
        righe.append("# Attenzione: poco testo estraibile (PDF a immagini?): consultare il PDF.")
    out = pdf.with_suffix(".txt")
    out.write_text("\n".join(righe) + "\n\n" + testo, encoding="utf-8")
    return out


def scarica_pdf(r: dict, fondi: dict[str, dict], browser: bool = False) -> tuple[bytes | None, str | None]:
    """Prova urllib, poi curl, poi (se richiesto) Chromium. Restituisce (PDF, None) oppure (None, errore)."""
    errore = None
    for modo in (["urllib", "curl"] + (["browser"] if browser else [])):
        try:
            if modo == "urllib":
                dati = _scarica_urllib(r["url"])
            elif modo == "curl":
                dati = _scarica_curl(r["url"])
            else:
                dati = _scarica_browser(r["url"], r["pagina"] or fondi[r["fondo_id"]]["url"])
            if dati.startswith(b"%PDF-"):
                return dati, None
            errore = f"{modo}: la risposta non è un PDF ({dati[:20]!r})"
        except Exception as e:  # rete, HTTP: si prova il modo successivo
            errore = f"{modo}: {e}"
    return None, errore


def scarica(args) -> int:
    righe, fondi = leggi_registro(), fondi_per_id()
    errori = valida(righe, fondi)
    if errori:
        print("\n".join(errori), file=sys.stderr)
        return 1
    oggi = dt.date.today().isoformat()
    falliti = 0
    for r in righe:
        if not r["file"] or (args.fondo and r["fondo_id"] not in args.fondo):
            continue
        pdf = CARTELLA / r["fondo_id"] / r["file"]
        nuovo = args.aggiorna or not pdf.exists()
        if nuovo:
            dati, errore = scarica_pdf(r, fondi, args.browser)
            if dati is None:
                falliti += 1
                print(f"ERRORE {r['fondo_id']}/{r['file']}: {errore}", file=sys.stderr)
                continue
            pdf.parent.mkdir(parents=True, exist_ok=True)
            pdf.write_bytes(dati)
        txt = pdf.with_suffix(".txt")
        if nuovo or not txt.exists():
            estrai_testo(pdf, r, fondi[r["fondo_id"]], oggi)
            print(f"OK {r['fondo_id']}/{r['file']} ({pdf.stat().st_size // 1024} KB)")
    print(f"Fatto: {falliti} download falliti." if falliti else "Fatto.")
    return 1 if falliti else 0


def riprova(args) -> int:
    """Riprova i documenti del registro non ancora scaricati (con un link): se ci riesce, scrive il PDF e il testo
    e aggiorna il registro (nome del file, nota svuotata). Utile da un'altra rete per i siti che bloccano i download."""
    righe, fondi = leggi_registro(), fondi_per_id()
    oggi = dt.date.today().isoformat()
    riusciti = 0
    for r in righe:
        if r["file"] or not r["url"] or r["tipo"] == NOTA_FONDO or (args.fondo and r["fondo_id"] not in args.fondo):
            continue
        dati, errore = scarica_pdf(r, fondi, args.browser)
        time.sleep(args.pausa)  # alcuni siti bloccano le richieste ravvicinate
        if dati is None:
            print(f"ancora no {r['fondo_id']} – {r['titolo'][:60]}: {errore}", file=sys.stderr)
            continue
        usati = {x["file"] for x in righe if x["fondo_id"] == r["fondo_id"] and x["file"]}
        nome, n = f"{r['tipo']}.pdf", 1
        while nome in usati:
            n += 1
            nome = f"{r['tipo']}-{n}.pdf"
        pdf = CARTELLA / r["fondo_id"] / nome
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf.write_bytes(dati)
        r["file"], r["note"] = nome, ""
        estrai_testo(pdf, r, fondi[r["fondo_id"]], oggi)
        riusciti += 1
        print(f"OK {r['fondo_id']}/{nome} ({len(dati) // 1024} KB)")
    if riusciti:
        with open(REGISTRO, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=CAMPI)
            w.writeheader()
            w.writerows(righe)
    print(f"Scaricati {riusciti} documenti: rigenera l'indice con 'python scripts/documenti.py indice'." if riusciti
          else "Nessun documento nuovo.")
    return 0


# ---------------------------------------------------------------- smistamento dei PDF aggiunti a mano
# Nomi con cui ogni fondo compare nei suoi documenti (testo normalizzato: minuscole, senza accenti né punteggiatura)
CHIAVI_FONDO = {
    "allianz-previdenza": ["allianz previdenza"], "previdenza-per-te": ["previdenza per te"], "almeglio-alleanza": ["almeglio"],
    "fondo-pensione-fideuram": ["fondo pensione fideuram"], "generali-global": ["generali global"],
    "previdsystem": ["previdsystem"], "teseo": ["teseo"], "destinazione-futuro-credemvita": ["destinazione futuro"],
    "vittoria-formula-lavoro": ["formula lavoro"], "arca-previdenza": ["arca previdenza"],
    "unipol-previdenza": ["unipol previdenza"], "vera-vita": ["vera vita"],
    "unicredit": ["unicredit fondo pensione aperto", "fondo pensione aperto unicredit"],
    "previgest-fund-mediolanum": ["previgest"], "zurich-contribution": ["zurich contribution"],
    "zed-omnifund": ["omnifund"], "plurifonds-itas-vita": ["plurifonds"], "eurorisparmio": ["eurorisparmio"],
    "aureo": ["aureo"], "credit-agricole-vita": ["fondo pensione aperto credit agricole", "credit agricole vita fondo pensione aperto"], "arti-e-mestieri": ["arti e mestieri"],
    "secondapensione": ["secondapensione"], "giustiniano": ["giustiniano"], "programma-open": ["programma open"],
    "il-mio-domani": ["il mio domani"], "azimut-previdenza": ["azimut previdenza"],
    "azione-di-previdenza": ["azione di previdenza"], "cnp": ["fondo pensione aperto cnp", "fpa cnp"],
    "insieme": ["fondo pensione aperto insieme", "insieme fondo pensione aperto"], "bim-vita": ["bim vita", "fondo pensione aperto bv"],
    "pensplan-profi": ["pensplan profi", "fondo pensione profi"], "raiffeisen": ["raiffeisen"],
    "il-melograno": ["melograno"], "ubi-previdenza": ["ubi previdenza"], "soluzione-previdente": ["soluzione previdente"],
    "bap-pensione-2007": ["bap pensione", "bappensione"], "core-pension": ["core pension"],
    "azimut-sustainable-future": ["sustainable future"],
}
# Titoli tipici, cercati all'inizio del documento (l'ordine conta: il Supplemento e le schede citano la Nota informativa)
TITOLI_TIPO = [
    ("supplemento", r"supplemento"), ("informativa-sostenibilita", r"informativa sulla sostenibilita"),
    ("scheda-costi", r"scheda i costi|scheda costi"), ("scheda-presentazione", r"scheda presentazione"),
    ("scheda-destinatari", r"destinatari e i contributi"), ("opzioni-investimento", r"opzioni di investimento"),
    ("soggetti-coinvolti", r"soggetti coinvolti"),
    ("documento-rendite", r"documento sull[ae]? ?(erogazione delle )?rendit|erogazione delle rendite|coefficienti di (trasformazione|conversione)"),
    ("documento-anticipazioni", r"documento sulle anticipazioni"), ("documento-regime-fiscale", r"regime fiscale"),
    ("documento-politica-investimento", r"politica di investimento"), ("documento-sistema-governo", r"sistema di governo"),
    ("metodologia-proiezioni", r"metodologia|proiezioni pensionistiche"), ("rendiconto", r"rendiconto"),
    ("modulo-adesione", r"modulo di adesione"), ("nota-informativa", r"nota informativa"), ("regolamento", r"regolamento"),
]
GENERICI = {"nota-informativa", "regolamento", "rendiconto"}  # citati anche nei titoli degli altri documenti


def _normalizza(t: str) -> str:
    import unicodedata
    t = re.sub(r"[’'`´]", " ", t.replace("&", " e "))
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _inizio_pdf(pdf: Path, pagine: int = 3) -> str:
    import logging
    from pypdf import PdfReader
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    try:
        r = PdfReader(pdf)
        if r.is_encrypted:
            r.decrypt("")
        return "\n".join((p.extract_text() or "") for p in r.pages[:pagine])
    except Exception:
        return ""


def riconosci(pdf: Path, fondi: dict[str, dict], cartella_fondo: str | None = None) -> dict:
    """Fondo (dalla sottocartella, altrimenti dal nome del file e dalle prime pagine) e tipo (dal titolo)."""
    testo = _normalizza(_inizio_pdf(pdf))
    nome = _normalizza(pdf.stem)
    if cartella_fondo in fondi:
        fondo, certezza = cartella_fondo, "cartella"
    else:
        punti = {}
        for fid, chiavi in CHIAVI_FONDO.items():
            n = sum(len(re.findall(rf"\b{re.escape(k)}\b", testo)) + 5 * len(re.findall(rf"\b{re.escape(k)}\b", nome))
                    for k in chiavi)
            if n:
                punti[fid] = n
        ordinati = sorted(punti.items(), key=lambda kv: -kv[1])
        fondo = ordinati[0][0] if ordinati else None
        certezza = ("unico" if len(ordinati) == 1 else "probabile" if ordinati[0][1] >= 2 * ordinati[1][1] else "dubbio") if ordinati else "nessuno"
    return {"fondo": fondo, "certezza": certezza, "tipo": _tipo(nome, testo[:1200]), "inizio": testo[:1200]}


def _tipo(nome: str, inizio: str) -> str:
    """Il tipo dal nome del file, se lo dice; altrimenti il titolo che compare per primo nel testo, preferendo una
    scheda o un allegato a "Nota informativa" se lo segue da vicino (es. "Nota informativa – Parte I – Scheda I costi")."""
    dal_nome = next((t for t, rx in TITOLI_TIPO if re.search(rx, nome)), None)
    if dal_nome:
        return dal_nome
    pos = {t: m.start() for t, rx in TITOLI_TIPO for m in [re.search(rx, inizio)] if m}
    if not pos:
        return "altro"
    primo = min(pos, key=pos.get)
    if primo in GENERICI:
        vicini = [t for t in pos if t not in GENERICI and 0 <= pos[t] - pos[primo] < 200]
        if vicini:
            primo = min(vicini, key=pos.get)
    return primo


def _somiglianza(a: str, b: str) -> float:
    pa = {w for w in _normalizza(a).split() if len(w) > 3}
    pb = {w for w in _normalizza(b).split() if len(w) > 3}
    return len(pa & pb) / len(pa) if pa else 0.0


def smista(args) -> int:
    righe, fondi = leggi_registro(), fondi_per_id()
    pdf_da_smistare = sorted(p for p in CASSETTA.rglob("*") if p.suffix.lower() == ".pdf")
    if not pdf_da_smistare:
        print(f"Nessun PDF in {CASSETTA.relative_to(ROOT)}/.")
        return 0
    oggi = dt.date.today().isoformat()
    usate = set()
    piano = []
    for pdf in pdf_da_smistare:
        sotto = pdf.parent.name if pdf.parent != CASSETTA else None
        ric = riconosci(pdf, fondi, sotto)
        fid = ric["fondo"]
        if not fid or ric["certezza"] in ("dubbio", "nessuno"):
            piano.append((pdf, ric, None, None))
            continue
        # il documento mancante del registro più simile (stesso tipo e titolo vicino al nome del file o all'inizio del testo)
        candidati = [r for r in righe if r["fondo_id"] == fid and not r["file"] and r["tipo"] != NOTA_FONDO and id(r) not in usate]
        def punteggio(r):
            return (r["tipo"] == ric["tipo"]) + max(_somiglianza(r["titolo"], pdf.stem), _somiglianza(r["titolo"], ric["inizio"]))
        migliore = max(candidati, key=punteggio, default=None)
        riga = migliore if migliore is not None and punteggio(migliore) >= 1.3 else None
        if riga is not None:
            usate.add(id(riga))
        tipo = riga["tipo"] if riga else ric["tipo"]
        presi = {r["file"] for r in righe if r["fondo_id"] == fid and r["file"]} | {n for _, _, n, x in piano if x == fid}
        nome, n = f"{tipo}.pdf", 1
        while nome in presi or (CARTELLA / fid / nome).exists():
            n += 1
            nome = f"{tipo}-{n}.pdf"
        piano.append((pdf, {**ric, "riga": riga}, nome, fid))
    for pdf, ric, nome, fid in piano:
        rel = pdf.relative_to(CASSETTA)
        if not nome:
            print(f"?  {rel}: fondo non riconosciuto con certezza ({ric['certezza']}): mettilo in una sottocartella con l'id del fondo")
            continue
        dest = f"{fid}/{nome}"
        if ric["riga"]:
            print(f"→  {rel} → {dest}  (documento mancante del registro: {ric['riga']['titolo'][:60]})")
        else:
            print(f"+  {rel} → {dest}  (nuovo documento, tipo {ric['tipo']}: controlla il titolo nel registro)")
    if not args.applica:
        print("Anteprima: per eseguire lo smistamento rilancia con --applica.")
        return 0
    nota = f"Copia fornita a mano il {oggi}: il sito non consente il download automatico."
    for pdf, ric, nome, fid in piano:
        if not nome:
            continue
        dest = CARTELLA / fid / nome
        dest.parent.mkdir(parents=True, exist_ok=True)
        riga = ric["riga"]
        if riga is None:
            riga = {"fondo_id": fid, "tipo": ric["tipo"], "titolo": pdf.stem.replace("_", " "), "file": "", "url": "",
                    "pagina": "", "referenziato": "No", "note": ""}
            righe.append(riga)
        pdf.replace(dest)
        riga["file"], riga["note"] = nome, nota
        estrai_testo(dest, riga, fondi[fid], oggi, provenienza="copia fornita a mano (non scaricata dallo script)")
    ordine = list(TIPI)
    pos = {f: i for i, f in enumerate(fondi)}
    righe.sort(key=lambda r: (pos.get(r["fondo_id"], 999), r["tipo"] == NOTA_FONDO, ordine.index(r["tipo"]) if r["tipo"] in TIPI else 0))
    with open(REGISTRO, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPI)
        w.writeheader()
        w.writerows(righe)
    print("Fatto: controlla data/documenti.csv (titoli dei documenti nuovi) e rigenera l'indice con 'python scripts/documenti.py indice'.")
    return 0


# ---------------------------------------------------------------- indice
def leggi_intestazione(txt: Path) -> dict:
    meta = {}
    with open(txt, encoding="utf-8") as fh:
        for riga in fh:
            if not riga.startswith("# "):
                break
            k, _, v = riga[2:].partition(": ")
            meta[k.strip()] = v.strip()
    return meta


def costruisci_indice(righe: list[dict], fondi: dict[str, dict]) -> tuple[dict, list[str]]:
    errori = valida(righe, fondi)
    ordine = list(TIPI)
    per_fondo: dict[str, list] = {fid: [] for fid in fondi}
    note_fondo: dict[str, str] = {}
    for r in righe:
        if r["tipo"] == NOTA_FONDO and r["fondo_id"] in fondi:
            note_fondo[r["fondo_id"]] = r["titolo"]
            continue
        if r["fondo_id"] not in fondi or r["tipo"] not in TIPI:
            continue
        doc = {
            "tipo": r["tipo"], "titolo": r["titolo"], "url": r["url"] or None,
            "pagina": r["pagina"] or fondi[r["fondo_id"]]["url"], "referenziato": r["referenziato"] == "Sì",
            "file": None, "testo": None, "scaricato_il": None, "pagine": None, "byte": None, "sha256": None,
            "note": r["note"] or None,
        }
        if r["file"]:
            pdf = CARTELLA / r["fondo_id"] / r["file"]
            txt = pdf.with_suffix(".txt")
            if not pdf.exists() or not txt.exists():
                errori.append(f"{r['fondo_id']}/{r['file']}: manca il PDF o il testo (python scripts/documenti.py scarica)")
            else:
                m = leggi_intestazione(txt)
                sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
                if m.get("SHA-256 del PDF") != sha:
                    errori.append(f"{r['fondo_id']}/{txt.name}: SHA-256 diverso dal PDF, rigenera il testo")
                doc.update({
                    "file": f"documenti/{r['fondo_id']}/{r['file']}", "testo": f"documenti/{r['fondo_id']}/{txt.name}",
                    "scaricato_il": m.get("Scaricato il"), "pagine": int(m.get("Pagine") or 0) or None,
                    "byte": pdf.stat().st_size, "sha256": sha,
                })
        per_fondo[r["fondo_id"]].append(doc)

    # file presenti nella cartella ma non nel registro
    attesi = {(r["fondo_id"], r["file"]) for r in righe if r["file"]}
    if CARTELLA.exists():
        for pdf in CARTELLA.glob("*/*.pdf"):
            if (pdf.parent.name, pdf.name) not in attesi:
                errori.append(f"{pdf.relative_to(ROOT)}: file non presente nel registro {REGISTRO.name}")

    out_fondi = []
    for fid, f in sorted(fondi.items(), key=lambda kv: kv[1]["riga"]):
        docs = sorted(per_fondo[fid], key=lambda d: (ordine.index(d["tipo"]), d["titolo"]))
        ref = [d for d in docs if d["referenziato"]]
        out_fondi.append({
            "fondo_id": fid,
            "referenziati": len(ref),
            "scaricati_referenziati": sum(1 for d in ref if d["file"]),
            "scaricati": sum(1 for d in docs if d["file"]),
            "nota": note_fondo.get(fid),
            "documenti": docs,
        })
    scaricati = [d for f in out_fondi for d in f["documenti"] if d["file"]]
    date = [d["scaricato_il"] for d in scaricati if d["scaricato_il"]]
    indice = {
        "aggiornato_il": max(date) if date else None,
        "tipi": [{"id": k, "nome": v[0], "descrizione": v[1]} for k, v in TIPI.items()],
        "totali": {
            "fondi": len(out_fondi),
            "fondi_con_documenti": sum(1 for f in out_fondi if f["scaricati"]),
            "referenziati": sum(f["referenziati"] for f in out_fondi),
            "scaricati_referenziati": sum(f["scaricati_referenziati"] for f in out_fondi),
            "scaricati": len(scaricati),
            "pagine": sum(d["pagine"] or 0 for d in scaricati),
            "byte": sum(d["byte"] for d in scaricati),
        },
        "fondi": out_fondi,
    }
    return indice, errori


def _mb(b: int) -> str:
    return f"{b / 1_048_576:.1f}".replace(".", ",") + " MB"


def scrivi_readme(indice: dict, fondi: dict[str, dict]) -> str:
    t = indice["totali"]
    nomi = {x["id"]: x["nome"] for x in indice["tipi"]}
    out = [
        "# Documenti ufficiali dei fondi",
        "",
        "<!-- File generato da scripts/documenti.py indice: non modificarlo a mano. -->",
        "",
        "Copie dei documenti pubblicati dai gestori nelle pagine informative dei fondi (elenco COVIP dei fondi pensione",
        "aperti), scaricate per consultarle e citarle. **Fa fede la versione pubblicata dal gestore**: ogni documento ha il",
        "link all'originale e la data in cui è stato scaricato. Accanto a ogni PDF c'è il testo estratto (`.txt`, con",
        "`=== pagina N ===` all'inizio di ogni pagina) per cercare e citare con il numero di pagina.",
        "",
        f"Totale: **{t['scaricati']} documenti** per {t['fondi_con_documenti']} fondi su {t['fondi']}, "
        f"{t['pagine']} pagine, {_mb(t['byte'])}. Dei {t['referenziati']} documenti citati nelle pagine ufficiali ne sono "
        f"stati scaricati {t['scaricati_referenziati']}. Registro delle fonti: [`data/documenti.csv`](../../data/documenti.csv).",
        "",
        "| Fondo | Scaricati / citati nella pagina ufficiale | Note |",
        "|---|---|---|",
    ]
    for f in indice["fondi"]:
        fondo = fondi[f["fondo_id"]]
        mancanti = [d for d in f["documenti"] if not d["file"]]
        note = "; ".join([f["nota"]] * bool(f["nota"]) + sorted({d["note"] for d in mancanti if d["note"]}))
        extra = f" (+{f['scaricati'] - f['scaricati_referenziati']} da altre pagine)" if f["scaricati"] > f["scaricati_referenziati"] else ""
        out.append(f"| [{fondo['nome_breve']}](#{f['fondo_id']}) | {f['scaricati_referenziati']} / {f['referenziati']}{extra} | {note} |")
    for f in indice["fondi"]:
        fondo = fondi[f["fondo_id"]]
        out += ["", f"## {fondo['nome_breve']}", "", f"<a id=\"{f['fondo_id']}\"></a>"
                f"{fondo['denominazione']} — [pagina ufficiale]({fondo['url']})", ""]
        if f["nota"]:
            out += [f"> {f['nota']}", ""]
        if not f["documenti"]:
            out.append("Nessun documento nel registro.")
            continue
        for d in f["documenti"]:
            nome = d["titolo"]
            if d["file"]:
                rel = d["file"].removeprefix("documenti/")
                out.append(f"- [{nome}]({rel}) · [testo]({d['testo'].removeprefix('documenti/')}) · {d['pagine']} pagine, "
                           f"scaricato il {d['scaricato_il']} da [{'questo link' if d['referenziato'] else 'una pagina diversa'}]({d['url']})"
                           + (f" — {d['note']}" if d["note"] else ""))
            else:
                link = f"[link]({d['url']})" if d["url"] else "nessun link"
                out.append(f"- {nome}: **non scaricato** ({link}) — {d['note']}")
    return "\n".join(out) + "\n"


def indice(args) -> int:
    fondi = fondi_per_id()
    ind, errori = costruisci_indice(leggi_registro(), fondi)
    for e in errori:
        print(f"ERRORE:  {e}", file=sys.stderr)
    if errori:
        return 1
    t = ind["totali"]
    print(f"OK: {t['scaricati']} documenti per {t['fondi_con_documenti']} fondi "
          f"({t['scaricati_referenziati']} su {t['referenziati']} citati nelle pagine ufficiali), {_mb(t['byte'])}.")
    if args.check:
        return 0
    testo = json.dumps(ind, ensure_ascii=False, indent=2) + "\n"
    for p in [INDICE] + ([] if args.no_docs else [INDICE_SITO]):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(testo, encoding="utf-8")
    CARTELLA.mkdir(parents=True, exist_ok=True)
    README.write_text(scrivi_readme(ind, fondi), encoding="utf-8")
    print(f"Scritti {INDICE.relative_to(ROOT)}, {README.relative_to(ROOT)}" + ("" if args.no_docs else f" e {INDICE_SITO.relative_to(ROOT)}"))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="comando", required=True)
    s = sub.add_parser("scarica", help="scarica i PDF mancanti ed estrae il testo")
    s.add_argument("--fondo", nargs="*", help="solo questi fondi (id di fondi.json)")
    s.add_argument("--aggiorna", action="store_true", help="riscarica anche i PDF già presenti")
    s.add_argument("--browser", action="store_true", help="se il download diretto fallisce, riprova con Chromium (Playwright)")
    s.set_defaults(func=scarica)
    rp = sub.add_parser("riprova", help="riprova i documenti non scaricati e aggiorna il registro")
    rp.add_argument("--fondo", nargs="*", help="solo questi fondi (id di fondi.json)")
    rp.add_argument("--browser", action="store_true", help="se il download diretto fallisce, riprova con Chromium (Playwright)")
    rp.add_argument("--pausa", type=float, default=3, help="secondi di attesa tra un download e l'altro (default 3)")
    rp.set_defaults(func=riprova)
    sm = sub.add_parser("smista", help="smista i PDF messi a mano in documenti-da-smistare/")
    sm.add_argument("--applica", action="store_true", help="esegue lo smistamento (senza: mostra solo cosa farebbe)")
    sm.set_defaults(func=smista)
    i = sub.add_parser("indice", help="rigenera data/documenti.json e docs/documenti/README.md")
    i.add_argument("--check", action="store_true", help="valida soltanto, senza scrivere file")
    i.add_argument("--no-docs", action="store_true", help="non copiare l'indice in docs/data/")
    i.set_defaults(func=indice)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
