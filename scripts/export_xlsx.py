#!/usr/bin/env python3
"""Esporta il workbook dei fondi pensione aperti (COVIP) in JSON per la dashboard.

Legge data/fondi-pensione-covip.xlsx (fonte di verità) e scrive:
  data/fondi.json, data/comparti.json, data/meta.json
e ne copia una versione in docs/data/ per il sito.

openpyxl non calcola le formule: lo script risolve da solo Comparti!A (=Sheet1!$A$n) e
ricalcola le metriche H–L di Sheet1, confrontandole con i valori in cache dell'ultimo
salvataggio in Excel (warning se diversi o assenti).

Uscita con codice 1 se ci sono errori di schema. Uso:
  python scripts/export_xlsx.py [--xlsx PERCORSO] [--out DIR] [--docs DIR | --no-docs] [--check] [--strict]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
XLSX_DEFAULT = ROOT / "data" / "fondi-pensione-covip.xlsx"

SHEET_FONDI = "Sheet1"
SHEET_COMPARTI = "Comparti"
FONDI_PRIMA_RIGA = 3      # intestazioni alla riga 2
COMPARTI_PRIMA_RIGA = 2   # intestazioni alla riga 1

CATEGORIE = ("AZN", "BIL", "OBB MISTO", "OBB PURO", "GAR")
PERIODI = (3, 5, 10)
SI_NO = ("Sì", "No")
ONLINE = ("Sì (Ciao Elsa)", "No", "No (lista d'attesa)")

# Intestazioni attese: se il workbook cambia struttura lo script si ferma invece di esportare dati sbagliati.
INTESTAZIONI_FONDI = {
    1: "Denominazione", 2: "Pagina informativa (URL)", 3: "Società (Ciao Elsa)",
    4: "Spese di adesione (€)", 5: "Spese annue fisse (€)", 6: "Costo % sul versato",
    7: "N. linee (dichiarate Ciao Elsa)", 8: "N. comparti nel foglio Comparti",
    9: "Comm. gestione min", 10: "Comm. gestione max", 11: "Max % azioni tra i comparti",
    12: "Miglior rendimento 10 anni", 13: "Linee sostenibili (ESG)", 14: "Life cycle",
    15: "Sottoscrizione online", 16: "Scheda Ciao Elsa (fonte)", 17: "Note",
}
INTESTAZIONI_COMPARTI = {
    1: "Fondo", 2: "Comparto", 3: "Categoria (Ciao Elsa)", 4: "% Azioni", 5: "% Obbligazioni",
    6: "Rendimento netto medio annuo", 7: "Periodo rendimento (anni)",
    8: "Commissione di gestione annua", 9: "Scheda Ciao Elsa (fonte)", 10: "Note",
}

# Codici delle anomalie rilevate in automatico (la descrizione finisce in meta.json per la UI).
FLAG_COMPARTI = {
    "somma_allocazione": "% azioni + % obbligazioni diversa da 100%",
    "garantito_azionario": "Comparto garantito/prudente con più del 50% di azioni",
    "categoria_incoerente": "% azioni incoerente con la categoria Ciao Elsa",
    "periodo_non_10": "Rendimento non a 10 anni: non confrontabile con gli altri",
    "rendimento_mancante": "Rendimento mancante",
    "commissione_mancante": "Commissione di gestione mancante",
}
FLAG_FONDI = {
    "linee_diverse": "N. linee dichiarate diverso dai comparti presenti nel foglio Comparti",
    "senza_dati": "Nessuna scheda né dati di dettaglio",
    "comparti_anomali": "Almeno un comparto ha anomalie: le metriche aggregate potrebbero essere falsate",
}

RE_RIF_FONDO = re.compile(r"^=\s*'?Sheet1'?!\$?A\$?(\d+)\s*$", re.IGNORECASE)
RE_GARANTITO = re.compile(r"garant|garanzia|prudent", re.IGNORECASE)
TOLLERANZA = 1e-9

# Parti generiche della denominazione COVIP, tolte per il nome breve mostrato nella UI.
RE_GENERICI = re.compile(
    r"\s*-?\s*FONDO PENSIONE APERTO\b|\bA CONTRIBUZIONE DEFINITA\b|\bPREVIDENZA COMPLEMENTARE\b"
    r"|\bIL FONDO PENSIONE APERTO DI\b|\bBY\b|\bFPA$",
    re.IGNORECASE,
)
PAROLE_MINUSCOLE = {"di", "e", "per", "il", "la", "a"}
SIGLE = {"BCC", "CNP", "BIM", "UBI", "BAP", "ZED", "ITAS", "FPA"}


class Report:
    def __init__(self) -> None:
        self.errori: list[str] = []
        self.warning: list[str] = []

    def errore(self, msg: str) -> None:
        self.errori.append(msg)

    def avviso(self, msg: str) -> None:
        self.warning.append(msg)


# ---------------------------------------------------------------- utilità

def slugify(testo: str) -> str:
    t = unicodedata.normalize("NFKD", testo).encode("ascii", "ignore").decode()
    t = t.replace("&", " e ")
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def nome_breve(denominazione: str) -> str:
    base = RE_GENERICI.sub(" ", denominazione)
    base = re.sub(r"\s+", " ", base).strip(" -")
    parole = []
    for i, p in enumerate(base.split(" ")):
        if p.upper() in SIGLE:
            parole.append(p.upper())
        elif i > 0 and p.lower() in PAROLE_MINUSCOLE:
            parole.append(p.lower())
        else:
            parole.append(p.capitalize())
    return " ".join(parole) or denominazione


def testo(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def numero(v, campo: str, dove: str, rep: Report) -> float | None:
    """Celle vuote → None (mai 0). Testo non numerico → errore."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, bool):
        rep.errore(f"{dove}: {campo} è un booleano ({v!r})")
        return None
    if isinstance(v, (int, float)):
        return float(v)
    rep.errore(f"{dove}: {campo} non numerico ({v!r})")
    return None


def arrotonda(v: float | None, cifre: int = 6) -> float | None:
    """Toglie il rumore binario (0.006500000000000001 → 0.0065)."""
    if v is None:
        return None
    r = round(v, cifre)
    return int(r) if r == int(r) and abs(r) >= 1 else r


def link(cell) -> str | None:
    if cell.hyperlink is not None and cell.hyperlink.target:
        return cell.hyperlink.target.strip()
    v = testo(cell.value)
    if v and re.match(r"^https?://", v):
        return v
    return None


def uguale(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= TOLLERANZA


def versione_app() -> str:
    """Versione pubblicata: APP_VERSION in CI (calcolata da scripts/versione.py), altrimenti git describe."""
    v = os.environ.get("APP_VERSION")
    if v:
        return v
    try:
        return subprocess.run(
            ["git", "describe", "--tags", "--match", "v*", "--always", "--dirty"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip() + " (sviluppo)"
    except (OSError, subprocess.CalledProcessError):
        return "sviluppo"


# Riconoscimento della licenza dal file LICENSE del repository (la UI non la scrive mai a mano).
LICENZE = [
    ("unencumbered software released into the public domain", "The Unlicense", "Unlicense"),
    ("mit license", "MIT License", "MIT"),
    ("apache license", "Apache License 2.0", "Apache-2.0"),
    ("gnu affero general public license", "GNU AGPL v3", "AGPL-3.0"),
    ("gnu lesser general public license", "GNU LGPL", "LGPL"),
    ("gnu general public license", "GNU GPL", "GPL"),
    ("mozilla public license", "Mozilla Public License 2.0", "MPL-2.0"),
    ("creative commons", "Creative Commons", "CC"),
]


def licenza_repo(rep: "Report") -> dict | None:
    f = ROOT / "LICENSE"
    if not f.exists():
        rep.avviso("File LICENSE assente: la licenza non viene mostrata nel sito")
        return None
    testo_lic = " ".join(f.read_text(encoding="utf-8", errors="replace").lower().split())
    for chiave, nome, spdx in LICENZE:
        if chiave in testo_lic:
            return {"nome": nome, "spdx": spdx, "file": "LICENSE"}
    rep.avviso("Licenza nel file LICENSE non riconosciuta: aggiungerla a LICENZE in export_xlsx.py")
    return {"nome": "vedi file LICENSE", "spdx": None, "file": "LICENSE"}


def git_commit() -> str | None:
    sha = os.environ.get("GITHUB_SHA")
    if sha:
        return sha
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


# ---------------------------------------------------------------- lettura

def verifica_intestazioni(ws, riga: int, attese: dict[int, str], rep: Report) -> None:
    for col, nome in attese.items():
        trovato = testo(ws.cell(riga, col).value)
        if trovato != nome:
            rep.errore(f"{ws.title}!{ws.cell(riga, col).coordinate}: intestazione {trovato!r}, attesa {nome!r}")


def leggi_fondi(ws, ws_cache, rep: Report) -> list[dict]:
    fondi = []
    for r in range(FONDI_PRIMA_RIGA, ws.max_row + 1):
        den = testo(ws.cell(r, 1).value)
        if den is None:
            if any(ws.cell(r, c).value is not None for c in range(2, 18)):
                rep.errore(f"Sheet1!A{r}: denominazione vuota in una riga con dati")
            continue
        dove = f"Sheet1 riga {r}"
        cache = {c: ws_cache.cell(r, c).value for c in range(8, 13)}
        n_linee = numero(ws.cell(r, 7).value, "N. linee", dove, rep)
        fondi.append({
            "id": None,  # assegnato dopo, garantendo l'unicità
            "riga": r,
            "denominazione": den,
            "nome_breve": nome_breve(den),
            "url": link(ws.cell(r, 2)),
            "societa": testo(ws.cell(r, 3).value),
            "spese_adesione": numero(ws.cell(r, 4).value, "Spese di adesione", dove, rep),
            "spese_annue": numero(ws.cell(r, 5).value, "Spese annue fisse", dove, rep),
            "costo_pct_versato": numero(ws.cell(r, 6).value, "Costo % sul versato", dove, rep),
            "n_linee": int(n_linee) if n_linee is not None else None,
            "esg": testo(ws.cell(r, 13).value),
            "life_cycle": testo(ws.cell(r, 14).value),
            "online": testo(ws.cell(r, 15).value),
            "scheda_url": link(ws.cell(r, 16)),
            "note": testo(ws.cell(r, 17).value),
            "_cache": cache,
        })
    return fondi


def leggi_comparti(ws, fondi_per_riga: dict[int, dict], fondi_per_nome: dict[str, dict], rep: Report) -> list[dict]:
    comparti = []
    for r in range(COMPARTI_PRIMA_RIGA, ws.max_row + 1):
        if all(ws.cell(r, c).value is None for c in range(1, 11)):
            continue
        dove = f"Comparti riga {r}"
        raw = ws.cell(r, 1).value
        fondo = None
        if isinstance(raw, str) and raw.startswith("="):
            m = RE_RIF_FONDO.match(raw)
            if not m:
                rep.errore(f"{dove}: formula in colonna A non riconosciuta ({raw!r}), attesa =Sheet1!$A$n")
            else:
                fondo = fondi_per_riga.get(int(m.group(1)))
                if fondo is None:
                    rep.errore(f"{dove}: {raw} punta a una riga di Sheet1 senza fondo")
        else:
            nome = testo(raw)
            fondo = fondi_per_nome.get(nome or "")
            if fondo is None:
                rep.errore(f"{dove}: fondo {nome!r} non trovato in Sheet1")
            else:
                rep.avviso(f"{dove}: colonna A contiene testo invece della formula =Sheet1!$A${fondo['riga']}")
        if fondo is None:
            continue
        periodo = numero(ws.cell(r, 7).value, "Periodo rendimento", dove, rep)
        comparti.append({
            "fondo_id": fondo["id"],
            "riga": r,
            "comparto": testo(ws.cell(r, 2).value),
            "categoria": testo(ws.cell(r, 3).value),
            "azioni": numero(ws.cell(r, 4).value, "% Azioni", dove, rep),
            "obbligazioni": numero(ws.cell(r, 5).value, "% Obbligazioni", dove, rep),
            "rendimento": numero(ws.cell(r, 6).value, "Rendimento", dove, rep),
            "periodo_anni": int(periodo) if periodo is not None else None,
            "commissione": numero(ws.cell(r, 8).value, "Commissione", dove, rep),
            "scheda_url": link(ws.cell(r, 9)),
            "note": testo(ws.cell(r, 10).value),
            "flag_anomalia": [],
        })
    return comparti


# ---------------------------------------------------------------- calcoli

def ricalcola_metriche(fondo: dict, suoi: list[dict]) -> None:
    """Equivalente Python delle formule H–L di Sheet1."""
    def valori(campo, filtro=lambda c: True):
        return [c[campo] for c in suoi if c[campo] is not None and filtro(c)]

    fondo["n_comparti"] = len(suoi)
    comm = valori("commissione")
    azioni = valori("azioni")
    rend10 = valori("rendimento", lambda c: c["periodo_anni"] == 10)
    vuoto = len(suoi) == 0
    fondo["comm_min"] = None if vuoto or not comm else min(comm)
    fondo["comm_max"] = None if vuoto or not comm else max(comm)
    fondo["max_azioni"] = None if vuoto or not azioni else max(azioni)
    fondo["best_rend_10a"] = max(rend10) if rend10 else None


def confronta_cache(fondo: dict, rep: Report, cache_vuote: list[str]) -> None:
    campi = {8: "n_comparti", 9: "comm_min", 10: "comm_max", 11: "max_azioni", 12: "best_rend_10a"}
    lettere = {8: "H", 9: "I", 10: "J", 11: "K", 12: "L"}
    for col, campo in campi.items():
        cella = f"Sheet1!{lettere[col]}{fondo['riga']}"
        in_cache = fondo["_cache"][col]
        calcolato = fondo[campo]
        if in_cache is None and fondo["n_comparti"] > 0:
            cache_vuote.append(cella)
            continue
        if in_cache == "":
            in_cache = None
        if isinstance(in_cache, str):
            rep.avviso(f"{cella}: valore in cache non numerico ({in_cache!r})")
            continue
        if col == 8 and in_cache is None:
            in_cache = 0 if fondo["n_comparti"] == 0 else None
        if not uguale(in_cache, calcolato):
            rep.avviso(f"{cella} ({campo}): in cache {in_cache!r}, ricalcolato {calcolato!r}")


def flag_comparto(c: dict) -> list[str]:
    flag = []
    a, o = c["azioni"], c["obbligazioni"]
    if a is not None and o is not None and abs(a + o - 1) > 0.005:
        flag.append("somma_allocazione")
    if a is not None and a > 0.5 and (RE_GARANTITO.search(c["comparto"] or "") or c["categoria"] == "GAR"):
        flag.append("garantito_azionario")
    if a is not None and "garantito_azionario" not in flag and (
        (c["categoria"] == "AZN" and a < 0.5)
        or (c["categoria"] in ("OBB PURO", "OBB MISTO", "GAR") and a > 0.5)
    ):
        flag.append("categoria_incoerente")
    if c["periodo_anni"] is not None and c["periodo_anni"] != 10:
        flag.append("periodo_non_10")
    if c["rendimento"] is None:
        flag.append("rendimento_mancante")
    if c["commissione"] is None:
        flag.append("commissione_mancante")
    return flag


# ---------------------------------------------------------------- validazione

def valida(fondi: list[dict], comparti: list[dict], rep: Report) -> None:
    ids = set()
    for f in fondi:
        dove = f"Sheet1 riga {f['riga']} ({f['nome_breve']})"
        if f["id"] in ids:
            rep.errore(f"{dove}: id duplicato {f['id']}")
        ids.add(f["id"])
        if not f["url"]:
            rep.errore(f"{dove}: manca la pagina informativa (colonna B)")
        for campo, ammessi in (("esg", SI_NO), ("life_cycle", SI_NO), ("online", ONLINE)):
            if f[campo] is not None and f[campo] not in ammessi:
                rep.errore(f"{dove}: {campo} = {f[campo]!r}, ammessi {ammessi}")
        for campo in ("spese_adesione", "spese_annue"):
            if f[campo] is not None and f[campo] < 0:
                rep.errore(f"{dove}: {campo} negativo")
        if f["costo_pct_versato"] is not None and not 0 <= f["costo_pct_versato"] < 1:
            rep.errore(f"{dove}: costo_pct_versato fuori da [0, 1)")
        if f["has_dati"] and not (f["scheda_url"] or f["note"]):
            rep.errore(f"{dove}: dati senza fonte (né scheda né nota)")

    for c in comparti:
        dove = f"Comparti riga {c['riga']}"
        if c["fondo_id"] not in ids:
            rep.errore(f"{dove}: fondo_id {c['fondo_id']} inesistente")
        if not c["comparto"]:
            rep.errore(f"{dove}: nome del comparto vuoto")
        if c["categoria"] not in CATEGORIE:
            rep.errore(f"{dove}: categoria {c['categoria']!r} non in {CATEGORIE}")
        for campo in ("azioni", "obbligazioni", "commissione"):
            v = c[campo]
            if v is not None and not 0 <= v <= 1:
                rep.errore(f"{dove}: {campo} = {v} fuori da [0, 1] (le percentuali sono decimali)")
        if c["commissione"] is not None and c["commissione"] > 0.05:
            rep.avviso(f"{dove}: commissione {c['commissione']:.2%} insolitamente alta")
        if c["rendimento"] is not None and not -0.5 <= c["rendimento"] <= 0.5:
            rep.errore(f"{dove}: rendimento {c['rendimento']} fuori scala (decimale atteso)")
        if c["periodo_anni"] not in (*PERIODI, None):
            rep.errore(f"{dove}: periodo_anni {c['periodo_anni']} non in {PERIODI}")
        if c["rendimento"] is not None and c["periodo_anni"] is None:
            rep.errore(f"{dove}: rendimento senza periodo")
        if not (c["scheda_url"] or c["note"]):
            rep.errore(f"{dove}: comparto senza fonte (né scheda né nota)")


# ---------------------------------------------------------------- main

def esporta(xlsx: Path, rep: Report) -> tuple[list[dict], list[dict], dict]:
    wb = openpyxl.load_workbook(xlsx)
    wb_cache = openpyxl.load_workbook(xlsx, data_only=True)
    for nome in (SHEET_FONDI, SHEET_COMPARTI):
        if nome not in wb.sheetnames:
            rep.errore(f"Foglio {nome!r} mancante (presenti: {wb.sheetnames})")
    if rep.errori:
        return [], [], {}

    ws_f, ws_c = wb[SHEET_FONDI], wb[SHEET_COMPARTI]
    verifica_intestazioni(ws_f, 2, INTESTAZIONI_FONDI, rep)
    verifica_intestazioni(ws_c, 1, INTESTAZIONI_COMPARTI, rep)
    if rep.errori:
        return [], [], {}

    fondi = leggi_fondi(ws_f, wb_cache[SHEET_FONDI], rep)
    usati: set[str] = set()
    for f in fondi:
        base = slugify(f["nome_breve"]) or f"fondo-{f['riga']}"
        sid, n = base, 2
        while sid in usati:
            sid, n = f"{base}-{n}", n + 1
        usati.add(sid)
        f["id"] = sid

    per_riga = {f["riga"]: f for f in fondi}
    per_nome = {f["denominazione"]: f for f in fondi}
    comparti = leggi_comparti(ws_c, per_riga, per_nome, rep)

    cache_vuote: list[str] = []
    for f in fondi:
        suoi = [c for c in comparti if c["fondo_id"] == f["id"]]
        ricalcola_metriche(f, suoi)
        confronta_cache(f, rep, cache_vuote)
    if cache_vuote:
        rep.avviso(
            f"{len(cache_vuote)} celle con formula senza valore in cache (file salvato fuori da Excel?): "
            "uso i valori ricalcolati in Python"
        )

    for c in comparti:
        c["flag_anomalia"] = flag_comparto(c)

    for f in fondi:
        suoi = [c for c in comparti if c["fondo_id"] == f["id"]]
        f["has_dati"] = f["n_comparti"] > 0 or f["societa"] is not None
        flag = []
        if not f["has_dati"]:
            flag.append("senza_dati")
        elif f["n_linee"] is not None and f["n_linee"] != f["n_comparti"]:
            flag.append("linee_diverse")
        if any(set(c["flag_anomalia"]) & {"somma_allocazione", "garantito_azionario", "categoria_incoerente"}
               for c in suoi):
            flag.append("comparti_anomali")
        f["flag_anomalia"] = flag

    valida(fondi, comparti, rep)

    ordine_fondi = [
        "id", "riga", "denominazione", "nome_breve", "url", "societa", "spese_adesione", "spese_annue",
        "costo_pct_versato", "n_linee", "n_comparti", "comm_min", "comm_max", "max_azioni", "best_rend_10a",
        "esg", "life_cycle", "online", "scheda_url", "note", "has_dati", "flag_anomalia",
    ]
    ordine_comparti = [
        "fondo_id", "riga", "comparto", "categoria", "azioni", "obbligazioni", "rendimento", "periodo_anni",
        "commissione", "scheda_url", "note", "flag_anomalia",
    ]
    numerici = {"spese_adesione", "spese_annue", "costo_pct_versato", "comm_min", "comm_max", "max_azioni",
                "best_rend_10a", "azioni", "obbligazioni", "rendimento", "commissione"}

    def pulisci(d: dict, ordine: list[str]) -> dict:
        return {k: (arrotonda(d[k]) if k in numerici else d[k]) for k in ordine}

    fondi_out = [pulisci(f, ordine_fondi) for f in fondi]
    comparti_out = [pulisci(c, ordine_comparti) for c in comparti]

    props = wb.properties
    modificato = props.modified.isoformat() if props.modified else None
    meta = {
        "versione": versione_app(),
        "generato_il": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "workbook": xlsx.name,
        "workbook_modificato_il": modificato,
        "workbook_sha256": hashlib.sha256(xlsx.read_bytes()).hexdigest(),
        "commit": git_commit(),
        "licenza": licenza_repo(rep),
        "conteggi": {
            "fondi": len(fondi_out),
            "fondi_con_dati": sum(f["has_dati"] for f in fondi_out),
            "comparti": len(comparti_out),
            "comparti_10_anni": sum(c["periodo_anni"] == 10 for c in comparti_out),
            "comparti_con_anomalie": sum(bool(c["flag_anomalia"]) for c in comparti_out),
            "fondi_con_anomalie": sum(bool(f["flag_anomalia"]) for f in fondi_out),
        },
        "flag": {"comparti": FLAG_COMPARTI, "fondi": FLAG_FONDI},
        "avvisi_export": rep.warning,
        "fonti": [
            {"nome": "COVIP – Elenco dei fondi iscritti all'Albo (Sezione II – Fondi pensione aperti)",
             "url": "https://www.covip.it/la-covip-e-la-sua-attivita/albo-fondi-pensione/elenco-fondi-albo", "tipo": "primaria",
             "dettaglio": "filtro Tipologia = Sezione II – Fondi pensione aperti"},
            {"nome": "Pagine informative dei gestori (Nota informativa, Scheda costi)", "url": None,
             "tipo": "primaria", "dettaglio": "colonna url di fondi.json"},
            {"nome": "Generali – confluenza di Almeglio in Generali Global dal 1/1/2027",
             "url": "https://www.generali.it", "tipo": "primaria"},
            {"nome": "Ciao Elsa – schede dei fondi pensione aperti",
             "url": "https://www.ciaoelsa.com/schede-fondo/fondi-pensione-aperti/", "tipo": "secondaria",
             "dettaglio": "colonna scheda_url di fondi.json e comparti.json"},
        ],
    }
    return fondi_out, comparti_out, meta


def scrivi_json(percorso: Path, dati) -> None:
    percorso.parent.mkdir(parents=True, exist_ok=True)
    percorso.write_text(json.dumps(dati, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", type=Path, default=XLSX_DEFAULT)
    ap.add_argument("--out", type=Path, default=ROOT / "data", help="cartella dei JSON generati")
    ap.add_argument("--docs", type=Path, default=ROOT / "docs" / "data",
                    help="cartella del sito in cui copiare i JSON")
    ap.add_argument("--no-docs", action="store_true", help="non copiare i JSON nel sito")
    ap.add_argument("--check", action="store_true", help="valida soltanto, senza scrivere file")
    ap.add_argument("--strict", action="store_true", help="tratta anche i warning come errori")
    args = ap.parse_args(argv)

    rep = Report()
    fondi, comparti, meta = esporta(args.xlsx, rep)

    for w in rep.warning:
        print(f"WARNING: {w}", file=sys.stderr)
    for e in rep.errori:
        print(f"ERRORE:  {e}", file=sys.stderr)
    if rep.errori or (args.strict and rep.warning):
        print(f"Export fallito: {len(rep.errori)} errori, {len(rep.warning)} warning.", file=sys.stderr)
        return 1

    c = meta["conteggi"]
    print(f"OK: {c['fondi']} fondi ({c['fondi_con_dati']} con dati), {c['comparti']} comparti, "
          f"{c['comparti_con_anomalie']} comparti segnalati, {len(rep.warning)} warning.")
    if args.check:
        return 0

    for cartella in [args.out] + ([] if args.no_docs else [args.docs]):
        scrivi_json(cartella / "fondi.json", fondi)
        scrivi_json(cartella / "comparti.json", comparti)
        scrivi_json(cartella / "meta.json", meta)
        print(f"Scritto in {cartella}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
