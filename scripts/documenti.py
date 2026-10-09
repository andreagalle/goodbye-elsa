#!/usr/bin/env python3
"""Documenti ufficiali dei fondi: download, testo estratto e indice per il sito.

Il registro data/documenti.csv (scritto a mano, una riga per documento) dice quali documenti cita la pagina
informativa ufficiale di ogni fondo e da dove si scaricano. Lo script:
  scarica  scarica in docs/documenti/<fondo-id>/<file> i PDF che mancano e ne estrae il testo in <file>.txt
           (intestazione con fonte, data, SHA-256 e numero di pagine, poi "=== pagina N ===" per ogni pagina),
           così si possono consultare e citare con il numero di pagina;
  indice   rigenera data/documenti.json (copiato in docs/data/ per il sito) e docs/documenti/README.md.
           Non usa la rete né pypdf: la CI lo esegue dopo l'export.

Uso:
  python scripts/documenti.py scarica [--fondo ID ...] [--aggiorna] [--browser]
  python scripts/documenti.py indice [--check] [--no-docs]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRO = ROOT / "data" / "documenti.csv"
FONDI = ROOT / "data" / "fondi.json"
CARTELLA = ROOT / "docs" / "documenti"
INDICE = ROOT / "data" / "documenti.json"
INDICE_SITO = ROOT / "docs" / "data" / "documenti.json"
README = CARTELLA / "README.md"

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
            if not r["url"]:
                errori.append(f"{dove}: file senza url di origine")
        elif not r["note"]:
            errori.append(f"{dove}: documento non scaricato senza una nota che spieghi perché")
    return errori


# ---------------------------------------------------------------- download e testo
def _scarica_urllib(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/pdf,*/*",
                                               "Accept-Language": "it-IT,it;q=0.9"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read()


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


def estrai_testo(pdf: Path, riga: dict, fondo: dict, scaricato_il: str) -> Path:
    from pypdf import PdfReader
    lettore = PdfReader(pdf)
    pagine = []
    for i, p in enumerate(lettore.pages, start=1):
        try:
            t = p.extract_text() or ""
        except Exception as e:  # pagine danneggiate: si segnala e si prosegue
            t = f"[testo non estraibile: {e}]"
        pagine.append(f"=== pagina {i} ===\n{t.strip()}\n")
    testo = "".join(pagine)
    nome_tipo = TIPI[riga["tipo"]][0]
    righe = [
        f"# Fondo: {fondo['denominazione']} ({fondo['id']})",
        f"# Documento: {nome_tipo} – {riga['titolo']}",
        f"# Fonte: {riga['url']}",
        f"# Citato in: {riga['pagina'] or fondo['url']}",
        f"# Scaricato il: {scaricato_il}",
        f"# SHA-256 del PDF: {hashlib.sha256(pdf.read_bytes()).hexdigest()}",
        f"# Pagine: {len(lettore.pages)}",
        INTESTAZIONE_TESTO,
    ]
    if len(re.sub(r"=== pagina \d+ ===|\s", "", testo)) < 50 * len(lettore.pages):
        righe.append("# Attenzione: poco testo estraibile (PDF a immagini?): consultare il PDF.")
    out = pdf.with_suffix(".txt")
    out.write_text("\n".join(righe) + "\n\n" + testo, encoding="utf-8")
    return out


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
            dati, errore = None, None
            for modo in (["urllib"] + (["browser"] if args.browser else [])):
                try:
                    dati = _scarica_urllib(r["url"]) if modo == "urllib" else _scarica_browser(r["url"], r["pagina"] or fondi[r["fondo_id"]]["url"])
                    if not dati.startswith(b"%PDF-"):
                        raise RuntimeError(f"la risposta non è un PDF ({dati[:20]!r})")
                    break
                except Exception as e:  # rete, HTTP, risposta non PDF: si prova il modo successivo
                    dati, errore = None, f"{modo}: {e}"
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
    for r in righe:
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
        note = "; ".join(f"{nomi[d['tipo']]}: {d['note']}" for d in mancanti)
        extra = f" (+{f['scaricati'] - f['scaricati_referenziati']} da altre pagine)" if f["scaricati"] > f["scaricati_referenziati"] else ""
        out.append(f"| [{fondo['nome_breve']}](#{f['fondo_id']}) | {f['scaricati_referenziati']} / {f['referenziati']}{extra} | {note} |")
    for f in indice["fondi"]:
        fondo = fondi[f["fondo_id"]]
        out += ["", f"## {fondo['nome_breve']}", "", f"<a id=\"{f['fondo_id']}\"></a>"
                f"{fondo['denominazione']} — [pagina ufficiale]({fondo['url']})", ""]
        if not f["documenti"]:
            out.append("Nessun documento nel registro.")
            continue
        for d in f["documenti"]:
            nome = f"{nomi[d['tipo']]} – {d['titolo']}"
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
    i = sub.add_parser("indice", help="rigenera data/documenti.json e docs/documenti/README.md")
    i.add_argument("--check", action="store_true", help="valida soltanto, senza scrivere file")
    i.add_argument("--no-docs", action="store_true", help="non copiare l'indice in docs/data/")
    i.set_defaults(func=indice)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
